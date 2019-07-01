"""
test local commands
"""
#===============================================================================
import os, sys
from click import echo
#===============================================================================
# Make sure that the current directory is the project directory.
# 'make test" and 'pytest' are generally run from the project directory.
# However, if we run/debug this file in eclipse, we end up in lore/tests
cwd = os.getcwd()
if cwd.endswith('tests'):
    echo(f"Changing current working directory"
         f"\n  from '{os.getcwd()}'"
         f"\n  to   '{os.path.abspath(os.path.join(os.getcwd(),'..'))}'.\n")
    os.chdir('..')
    cwd = os.getcwd()
assert os.path.exists('./tests')
project_dir = os.path.basename(cwd)
test_dir = os.path.join(cwd,'tests')
test_data_dir = os.path.join(test_dir,'data')
# Make sure that we can import the module being tested. When running
# 'make test" and 'pytest' in the project directory, the current working
# directory is not automatically added to sys.path.
if not ('.' in sys.path or os.getcwd() in sys.path):
    echo(f"Adding '.' to sys.path.\n")
    sys.path.insert(0, '.')
#===============================================================================
from lore                import run, Connection,__version__
from lore.postprocessors import list_of_lines,list_of_non_empty_lines
from lore.commands       import ensure_dir,exists,remove,touch, glob,rename,env
from lore.exceptions     import NonZeroReturnCode, Stderr, CommandTimedOut, RepeatedExecutionFailed
from lore.commands       import copy_local_to_remote
#===============================================================================
from types import SimpleNamespace
me = SimpleNamespace( username = 'vsc20170'
                    , sshkey   = '/Users/etijskens/.ssh/et_rsa'
                    )
#===============================================================================
leibniz1 = Connection( login_node='login1-leibniz.uantwerpen.be'
                                   , username  =me.username
                                   , ssh_key   =me.sshkey
                                   )
#===============================================================================
import pytest
#===============================================================================    
# setup a logger which writes to stderr and to file lore.log.txt
import logging
lore_log = logging.getLogger('lore_log')
logfile_handler = logging.FileHandler("lore.log.txt",mode='w')
logfile_formatter = logging.Formatter(f"%(levelname)s: %(name)s (lore v{__version__}) : %(asctime)s %(message)s\n")
logfile_handler.setFormatter(logfile_formatter)
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.INFO)
stderr_formatter = logging.Formatter(f"%(levelname)s: %(name)s (lore v{__version__}) %(message)s\n")
stderr_handler.setFormatter(stderr_formatter)
lore_log.addHandler(logfile_handler)
lore_log.addHandler(stderr_handler)
#===============================================================================
# tests
#===============================================================================
def try_interactive_connection():
    leibniz2 = Connection('login1-leibniz.uantwerpen.be')
    assert leibniz2.is_connected()
#===============================================================================
def test_echo():
    s = 'hello world'
    cmd = 'echo '+s
    result = run(cmd,connection=leibniz1)
    assert result.returncode==0
    assert result.stderr==''
    assert result.stdout==s+'\n'
#===============================================================================
def test_printf_2_lines():
    s = 'hello world\nhow do you do?\n'
    cmd = f"printf '{s}'"
    result = run(cmd,connection=leibniz1)
    assert result.returncode==0
    assert result.stderr==''
    assert result.stdout==s
#===============================================================================
def test_list_of_lines():
    s = 'hello world\n\nhow do you do?\n'
    cmd = f"printf '{s}'"
    result = run(cmd,post_processor=list_of_lines,connection=leibniz1)
    assert result.returncode==0
    assert result.stderr==''
    expected = s.splitlines(keepends=False)
    expected.append('')
    assert result.processed==expected
#===============================================================================
def test_list_of_non_empty_lines():
    s = 'hello world\n\nhow do you do?\n'
    cmd = f"printf '{s}'"
    result = run(cmd,post_processor=list_of_non_empty_lines,connection=leibniz1)
    assert result.returncode==0
    assert result.stderr==''
    expected = s.splitlines(keepends=False)
    expected = [line for line in expected if line]
    assert result.processed==expected
#===============================================================================
def test_exists_existing():
    assert exists('data',connection=leibniz1)
#===============================================================================
def test_exists_inexisting():
    assert not exists('inexisting',connection=leibniz1)
#===============================================================================
def test_ensure_dir_existing():
    assert exists('data',connection=leibniz1)
    ensure_dir   ('data',connection=leibniz1)
    assert exists('data',connection=leibniz1)
#===============================================================================
def test_ensure_dir_inexisting():
    # make sure that inexisting does not yet exists
    inexisting = os.path.join('data','inexisting')
    if exists(inexisting,connection=leibniz1):
        remove(inexisting,connection=leibniz1)
    assert not exists(inexisting,connection=leibniz1)
    
    # make inexisting and check
    ensure_dir(inexisting,connection=leibniz1)
    
    assert exists(inexisting,connection=leibniz1)
    
    # clean up
    remove(inexisting,connection=leibniz1)
    assert not exists(inexisting,connection=leibniz1)
#===============================================================================
def test_ls_inexisting():
    # ls on a inexisting directory produces a nonzero return code (1), and a
    # diagnostic message on stderr
    cmd = f"ls {os.path.join('data','inexisting')}"
    with pytest.raises(NonZeroReturnCode):
        try:
            run(cmd,connection=leibniz1)
        except NonZeroReturnCode as e: 
            assert e.result.returncode != 0
            assert bool(e.result.stderr)
            raise
    with pytest.raises(Stderr):
        try:
            run(cmd,stderr_is_error=True,check=False,connection=leibniz1)
        except Stderr as e:
            assert e.result.returncode != 0
            assert bool(e.result.stderr)
            raise
#===============================================================================
def test_no_timeout():
    # this must not timeout
    timeout = 5
    sleep = timeout/4
    cmd = f"sleep {sleep}"
    result = run(cmd,connection=leibniz1,timeout=timeout)
    assert result.returncode == 0
    assert not bool(result.stdout)
    assert not bool(result.stderr)
#===============================================================================
def test_timeout(): 
    # this must timeout
    cmd = 'tree data'
    with pytest.raises(CommandTimedOut):
        run( cmd, connection=leibniz1
           , timeout=0.1
           , error_log=lore_log
           )
#===============================================================================
def test_repeated_execution_fails():
    with pytest.raises(RepeatedExecutionFailed):
        try:
            run( "sleep 1",connection=leibniz1
               , attempts=3, wait=.5
               , timeout=.9
               , verbose=True
               , error_log=lore_log
               )
        except RepeatedExecutionFailed as e:
            print(e)
            raise
#===============================================================================
def test_repeated_execution_succeeds():
    # setup
    newdir = os.path.join('data', 'newdir')
    try:
        remove(newdir, leibniz1)
    except:
        pass
    assert not exists(newdir, leibniz1)
    
    src_sh = os.path.join(test_data_dir,'test_succeeds_the_second_time.sh')
    assert exists('data',leibniz1)
    dst_sh = os.path.join('data','test_succeeds_the_second_time.sh')
    remove(dst_sh,leibniz1)
    copy_local_to_remote(leibniz1,src_sh,dst_sh)    
    assert     exists(dst_sh,leibniz1)
    assert not exists(dst_sh,leibniz1,operator='-x')
    run('chmod +x test_succeeds_the_second_time.sh',leibniz1,working_directory='data')
    assert     exists(dst_sh,leibniz1,operator='-x')
    
    # test 
    # this command should succeeds the second time
    cmd = "./test_succeeds_the_second_time.sh"
    result = run( cmd, leibniz1, working_directory='data'
                , attempts=3, wait=.5
                , verbose=True
                )
    assert result.attempts == 2
    assert exists(newdir,leibniz1)
         
    # clean up
    remove(newdir,leibniz1)
    assert not exists(newdir,leibniz1)
    remove(dst_sh,leibniz1)
    assert not exists(dst_sh,leibniz1)
#===============================================================================
def test_touch():
    path = os.path.join('data','touch')
    if exists(path,connection=leibniz1):
        remove(path,connection=leibniz1)
    ensure_dir(path,connection=leibniz1)
    
    for file in ['a.txt','b.txt','c.txt']:
        touch(file,path=path,connection=leibniz1)
    for file in ['a.txt','b.txt','c.txt']:
        p = os.path.join(path,file)
        assert exists(p,connection=leibniz1)
        
    remove(path,connection=leibniz1)
#===============================================================================
def test_glob():
    path = os.path.join('data','glob')
    if exists(path,connection=leibniz1):
        remove(path,connection=leibniz1)
    ensure_dir(path,connection=leibniz1)
    files = ['a.txt','b.txt','c.txt','aa.txt']
    for file in files:
        touch(file,path=path,connection=leibniz1)
    dirs =['a.tx','d.txt']
    for folder in dirs:
        ensure_dir(os.path.join(path,folder),connection=leibniz1)
        
    result = glob('*.txt',path=path,connection=leibniz1)
    assert len(result)==4
    for file in result:
        assert file in files
         
    result = glob('?.txt',path=path,connection=leibniz1)
    assert len(result)==3
    for file in result:
        assert file in files
        
    # clean up
    remove(path,connection=leibniz1)
#===============================================================================
def test_rename():
    # set up
    test_dir = os.path.join('data','rename')
    ensure_dir(test_dir,connection=leibniz1)
    old = os.path.join(test_dir,'old.txt')
    touch(old,connection=leibniz1)
    assert exists(old,connection=leibniz1)
    
    # test
    new = os.path.join(test_dir,'new.txt')
    rename(old,new,connection=leibniz1)
    assert not exists(old,connection=leibniz1)
    assert     exists(new,connection=leibniz1)
    
    # clean up
    remove(test_dir,connection=leibniz1)
#===============================================================================
def test_env():
    user = env( 'USER',connection=leibniz1)
    assert user == 'vsc20170'

    user = env('$USER',connection=leibniz1)
    assert user == 'vsc20170'
    
    unknown = env( 'varthatdoesnotexist',connection=leibniz1)
    assert unknown == ''
    
    unknown = env('$varthatdoesnotexist',connection=leibniz1)
    assert unknown == ''
#===============================================================================
    
#===============================================================================
# The code below is for debugging a particular test in eclipse/pydev.
# (Typically, all tests are run with pytest form the command line)
#===============================================================================
if __name__=="__main__":
#     the_test_you_want_to_debug = try_interactive_connection
    the_test_you_want_to_debug = test_repeated_execution_succeeds

    from execution_trace import trace
    with trace(f"__main__ running {the_test_you_want_to_debug}",'-*# finished #*-',singleline=False,combine=False):
        the_test_you_want_to_debug()
#===============================================================================


