"""
Bash command wrappers
=====================
Some wrappers for common bash commands. Where possible the Python standard 
library has been used for mimicking local os commands.

All commands take an optional *connection* parameter, which, if equalling *None*,
has the command executed locally, and remotely otherwise.
"""
#===============================================================================    
import os,errno,shutil,fnmatch
#===============================================================================    
from lrcmd import run
try:
    from lrcmd.remote import RemoteCommand
except ModuleNotFoundError:
    RemoteCommand = None
from lrcmd.postprocessors import list_of_lines
from lrcmd.exceptions import NonZeroReturnCode, CommandTimedOut
from execution_trace import trace
from click           import echo
#===============================================================================
def exists(p, connection=None, operator=None):
    """
    Test if a path *p* to a file or directory exists locally (*connection=None*) 
    or remotely on *connection*.
    
    :param str p: path to file or directory
    :param Connection connection: if None, the command acts locally, 
        otherwise it is remotely as specified by *connection*.
    :param str operator: one of the 
        `bash file test operators <https://www.tldp.org/LDP/abs/html/fto.html>`_ 
        that will be used to execute the test. E.g. *operator='-x'* test if *p* 
        is executable.
    :rtype: bool
    """
    if operator is None:
        if connection is None:
            return os.path.exists(p)
        else:
            cmd = f"[ -e {p} ]"
            try:
                run(cmd,connection) # may raise NotConnected
                return True
            except NonZeroReturnCode:
                return False
    else:
        cmd = f"[ {operator} {p} ]"
        try:
            run(cmd,connection) # may raise NotConnected
            return True
        except NonZeroReturnCode:
            return False
#===============================================================================
def ensure_dir(p,connection=None):
    """
    Create a directory path *p*, if it does not already exist, and return it. 
    
    :param str p: the directory path that must be ensured.
    :param Connection connection: if None, the command acts locally, 
        otherwise it is remotely as specified by *connection*.
    :return: *p*
    """
    if isinstance(p,(list,tuple)):
        p = os.path.join(*p)
    if not connection:
        # local version
        # see https://stackoverflow.com/questions/273192/how-can-i-safely-create-a-nested-directory-in-python
        try:
            os.makedirs(p)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
    else:
        #remote version
        cmd = 'mkdir -p '+p
        run(cmd,connection) 
        # may raise NotConnected
        # no error if the path already exists. 
    return p
#===============================================================================
def remove(p,connection=None):
    """
    Remove a file or a directory (with its contents if non-empty).
    
    :param str p: path to a file or directory (not necessarily empty) that will
        be removed
    :param Connection connection: if None, the command acts locally, 
        otherwise it is remotely as specified by *connection*.
    """
    if connection is None:
        # local remove
        shutil.rmtree(p)
    else:
        # remote remove
        cmd = 'rm -rf '+p
        run(cmd,connection)
#===============================================================================    
def touch(file,path='.',connection=None):
    """
    Create a new empty file. If *path* does not already exist, it is created. 
    
    :param str file: name of the file to create.
    :param str path: optional path, where the file must be created. If the path
        does not yet exist, it is created.
    :param Connection connection: if None, the command acts locally, 
        otherwise it is remotely as specified by *connection*.
    """
    ensure_dir(path, connection=connection)
    cmd = "touch "+os.path.join(path,file)
    run(cmd,connection=connection)
#===============================================================================    
def glob(pattern,path='.',connection=None):
    """
    Local or remote glob accepting 
    `Unix-like wildcards <https://docs.python.org/3.4/library/fnmatch.html>`_ . 
     
    :param str pattern: filename pattern to be matched.
    :param str path: path to the directory whose files are examined. By default
        glob looks in the current working directory (local glob) or in the remote 
        home directory (remote glob). 
    :param Connection connection: if None, the command acts locally, 
        otherwise it is remotely as specified by *connection*.
    :return: a *list* of all filenames that match *pattern* in directory *path*.
    """
    cmd = f"find {path} -maxdepth 1 -type f"
    files = run(cmd,connection=connection,post_processor=list_of_lines).processed
    result =[]
    for file in files:
        filename = os.path.basename(file)
        if fnmatch.fnmatch(filename,pattern):
            result.append(filename)
    return result
#===============================================================================    
def rename(src,dst,connection=None):
    """
    Rename a directory or file.
    
    :param str src: path to directory or file to be renamed
    :param str dst: new path
    :param Connection connection: if None, the command acts locally, 
        otherwise it is remotely as specified by *connection*.
    """
    if connection is None:
        # local rename
        os.rename(src,dst)
    else:
        # remote rename
        cmd = f'mv {src} {dst}'
        run(cmd,connection)
#===============================================================================
def env(var,connection=None):
    """
    Resolve an environment variable *var*.
    
    :param str var: name of the environment variable
    :param Connection connection: if None, the command acts locally, 
        otherwise it is remotely as specified by *connection*.
    :return: str with the environment variable's value. If if does not exist an 
        empty str is returned (no KeyError is raised).
        
    """
    if connection is None:
        if var[0]=='$':
            var = var[1:]
        try:
            val = os.environ[var]
        except KeyError:
            val = ''
    else:
        if var[0]=='$':
            cmd = 'echo '+var
        else:
            cmd = 'echo $'+var
        result = run(cmd,connection)
        val = result.stdout[:-1]
    return val
#===============================================================================
def copy_local_to_remote(connection,local_source,remote_destination
                        ,timeout=None
                        ):
    """
    Copy a local file or directory to a remote file or directory. If local_source
    refers to a directory, it is tarred, copied, and untarred. Finally, the .tar
    files are removed. 
    
    :param Connection connection:
    :param str local_source: path to the local file.
    :param str remote_destination: path to remote file (filename must be included). 
    :param int timeout: timeout for the compression command in seconds.
    
    **Warning** : Make sure that during login nothing writes to stdout. That will 
    mess up the sftp protocol.
    """
    assert(os.path.exists(local_source))

    if os.path.isdir(local_source):
        # copy whole directory, by first compressing it, copying the compressed file,
        # and decompressing it at the remote location. If successfull, the compressed
        # files are removed.
        
        # split local path in parent and directory:
        if local_source.endswith('/'): # remove trailing '/'
            local_source = local_source[:-2]
        local_parent,local_dir = os.path.split(local_source)
        
        # split remote path in parent and directory:
        if remote_destination.endswith('/'): # remove trailing '/'
            remote_destination = remote_destination[:-2]
        remote_parent,remote_dir = os.path.split(remote_destination)
        
        #verify that the remote parent exists:
        assert exists(remote_parent, connection), f"Inexisting remote path: '{remote_parent}'"
        
        # compress the directory:
        # don't use verbose option (v), it write to stderr and hence raises a Stderr exception 
        with trace(f'compressing "{local_dir}"'):
            cmd = f'tar -zcf {local_dir}.tar.gz {local_dir}'
            try:
                run(cmd,working_directory=local_parent,timeout=timeout)
            except CommandTimedOut:
                raise Exception('\nThe command'
                               f'\n  {cmd}'
                               f'\nfailed to complete in {timeout} s.'
                                '\nLarge files may take a substantial amount of time to compress.'
                                '\nTry increasing the timeout parameter.'
                               )
            local_source_compressed = f'{local_source}.tar.gz'
            # verify that the compressed file exists:
            assert(os.path.exists(local_source_compressed))
        
        # copy the compressed file:
        with trace(f'Copying "{local_dir}"'):
            remote_destination_compressed = f'{remote_destination}.tar.gz'
            copy_local_to_remote(connection,local_source_compressed,remote_destination_compressed)
            # verify that the copy exists:
            cmd = f'ls {remote_destination_compressed}'
            run(cmd,connection) # raises Stderr if the copy is not there
        
        # extract the archive
        with trace(f"Extracting '{local_dir}'"):
            cmd = f'tar -zxvf {remote_dir}.tar.gz {remote_dir}'
            run(cmd,connection,working_directory=remote_parent)
        
        # clean up the local and remote tar files
        with trace('Cleaning up'):
            os.remove(f'{local_source}.tar.gz')
            cmd = f'rm {remote_destination}.tar.gz'
            run(cmd,connection)
            
        echo(f'copied "{local_source}" to "{remote_destination}"', err=True)
    else:
        sftp = connection.paramiko_client.open_sftp()
        sftp.put(local_source, remote_destination)
        #   disk quota exceeded may cause this to fail...
        sftp.close()
#===============================================================================
def copy_remote_to_local(connection,local_destination,remote_source,rename=False):
    """
    Copy a remote file *remote_source* to local file *local_destination*. 
    Optionally, *remote_source* can be renamed, e.g. to mark the file as copied, 
    by specifying the *rename* parameter. Possible values are:

    :param Connection connection: a Connection object to a remote machine.
    :param str local_destination: filepath of the local destination file
    :param str remote_source: filepath of the remote source file
    :param str rename: either *False*, '' (empty string) or non-empthy string.
        If *rename==False*, the original file is just kept, as is. If *rename*
        is the empty string, the original file is removed, and if *rename* is 
        a non-empty string, thatwill be the name (and location, as in the linux
        *mv* command) of the file after it is copied.
    """
    sftp = connection.paramiko_client.open_sftp()
    sftp.get(remote_source,local_destination)
    sftp.close()
    
    if isinstance(rename,str):
        if rename:
            command = f'mv {remote_source} {rename}'
        else:
            command = 'rm -f '+remote_source
        cmd = RemoteCommand(connection,command)
        cmd.execute()
    else:
        if not (isinstance(rename,bool) and rename==False):
            raise ValueError(f"kwarg 'rename' must be str or False, got '{rename}'.")
#===============================================================================
def copy_glob_remote_to_local(connection
                             ,local_destination,remote_source
                             ,pattern='*'
                             ,force_overwrite=False
                             ,verbosity=0
                             ):
    """
    Copy all remote files in *remote_source* matching *pattern* to 
    *local_destination*. 
     
    :param Connection connection: a Connection object to a remote machine
    :param str local_destination: directory path of local destination directory
    :param str remote_source: directory path of remote source directory
    :param str pattern: glob pattern to select the files that will be copied
    :param bool force_overwrite: overwrite any existing files in the local destination directory
    :param int verbosity: 0=silent, 1, 2
    """
    files = glob(connection, pattern, remote_source)
    ensure_dir(local_destination)
    copied = 0
    not_copied = 0
    if verbosity==1:
        echo('> Copying from ' + remote_source    , err=True)
        echo('>           to ' + local_destination, err=True)
    for file in files:
        local_destination_file = os.path.join(local_destination,file)
        remote_source_file     = os.path.join(remote_source    ,file)
        if force_overwrite or not os.path.exists(local_destination_file):
            if verbosity>0:
                echo('>      copying ' + file)
                if verbosity>1:
                    echo('>    from ' + remote_source    , err=True)
                    echo('>      to ' + local_destination, err=True)
            copy_remote_to_local(connection,local_destination_file,remote_source_file)
            copied += 1
        else:
            not_copied += 1
    if verbosity>0:
        echo(f'> {copied} files copied')
        if not force_overwrite:
            echo(f'> {not_copied} files not copied')
            if verbosity>1:
                echo('> If you want to overwrite pre-existing files, specify force_overwrite=True.', err=True)            
#===============================================================================
