# -*- coding: utf-8 -*-

"""
Package lrcmd
=============

Module lrcmd provides a unified interfaces executing OS commands locally (using 
and remotely over ssh. This achieved by wrapping the standard library's 
subprocess module for local commands, and by wrapping 
`paramiko <http://docs.paramiko.org>`_.

* lrcmd.commands: wrappers of common bash commands, and methods to copy 
  between local and remote machines.
* lrcmd.postprocessors: some functions to treat the output of a command on 
  stdout.
* lrcmd.exceptions: exceptions used by lrcmd.
"""
#===============================================================================
__version__ = "0.2.1"
#===============================================================================
import subprocess,os,errno,sys
#===============================================================================
from click import prompt,confirm,echo
#===============================================================================    
from .exceptions import NotConnected, NonZeroReturnCode, Stderr
from .local      import LocalCommand
#===============================================================================    
try:
    import paramiko
except ImportError:
    print("Warning lrcmd:\n  Module paramiko is not available."
           "\n  To allow for remote commands, either install paramiko, or"
           "\n  actixvate a Python environment which has paramiko installed."
          , file=sys.stderr
          )
    RemoteCommand = None
else:
    from lrcmd.remote import RemoteCommand
#===============================================================================
def run( command, connection=None
                , working_directory='.'
                , check=True
                , stderr_is_error=False
                , timeout=None
                , error_log=None
                , post_processor=None
                , attempts=1
                , wait=0
                , verbose=True 
                ):
    """
    Wrapper function around LocalCommand (*connection=None*) and RemoteCommand 
    (*connection=some_Connection_object*). Provides a common interface to execute 
    *command* locally or remotely.
    
    :param str command: the command as you would type it in a terminal.
    :param Connection connection: if None *command* is run locally,
        otherwise it is run remotely through the *connection* . 
    :param str working_directory: directory where *command* is run. For 
        remote commands a relative working directory path is relative to the
        remote directory where you would normally end up when you ssh to the
        remote machine in a terminal.
    :param bool check: check the return code of the command and raise 
        lrcmd_exceptions.NonZeroReturnCode if different from 0. 
    :param bool stderr_is_error: raise lrcmd_exceptions.Stderr if there is
        output on stderr. 
    :param int timeout: the number of seconds in which the command must completed. 
        If it doesn't, a *lrcmd.exceptions.CommandTimedOut* is raised. Default
        is None, implying no timeout.
    :param post_processor: a function that transforms the output (on stdout) of 
        *command* .
    :param int attempts: number of times the command is retried on failure. 
    :param int wait: seconds of wait time after the first failure, doubled on 
        every failure.
    
    :return: on success, an object containing returncode, stdout and stderr as 
        members.
      
    """
    if connection is None:
        cmd = LocalCommand(command,working_directory=working_directory)
    else:
        cmd = RemoteCommand(connection,command,working_directory=working_directory)
    
    if attempts==1:
        result = cmd.execute( post_processor  = post_processor
                            , check           = check
                            , stderr_is_error = stderr_is_error
                            , timeout         = timeout
                            , error_log       = error_log
                            )
    else:
        result = cmd.execute_repeat( attempts        = attempts
                                   , wait            = wait
                                   , post_processor  = post_processor
                                   , check           = check
                                   , stderr_is_error = stderr_is_error
                                   , timeout         = timeout
                                   , error_log       = error_log
                                   , verbose         = verbose
                                   )

    return result
    #---------------------------------------------------------------------------
    
#===============================================================================
class Connection:
    """
    Class for managing a `paramiko <http://docs.paramiko.org>`_ (ssh) connection 
    to some remote machine, e.g. the login node of a HPC cluster:
    
    :param str login_node: name of the login node as it would appear in a manual
        ssh command.
    :param str username: username you would use to ssh to the remote machine
        in a terminal command. If *None*, you are prompted to enter it 
        interactively. 
    :param str ssh_key: filepath of your ssh key. If it contains a path 
        separator (typically '/'), it is treated as an absolute file path, 
        otherwise the key is assumed to be in '~/.ssh/'. If the key does not exist,
        the user is prompted again. Pressing `enter` without entering a key exits 
        the process and raises *NotConnected* .
    :param str passphrase: optional passphrase to unlock the ssh key.
    :param bool verbose: prints a message to stderr on successfull connection.
    :param str label: extra information added to self.label, which by default 
        contains *'username@login_node'* .
    """
    #---------------------------------------------------------------------------    
    def __init__( self, login_node
                , username=None, ssh_key=None, passphrase=None
                , verbose=False
                , label=None
                ):
        """
        Open a connection
        """
        if username is None or ssh_key is None:
            echo(f"Interactively connecting to {login_node} ...", err=True) 
            if username is None:
                username = prompt("  Enter username")
            while ssh_key is None:
                ssh_key    = prompt(f"  Enter ssh key filename for user {username}"
                                   , default=''
                                   )
                if not ssh_key:
                    raise NotConnected("You ended the connection process by not providing a ssh key.")
                ssh_key = os.path.expanduser(ssh_key)
                if not os.sep in ssh_key:
                    ssh_key = os.path.expanduser(os.path.join('~/.ssh',ssh_key))
                if not os.path.exists(ssh_key):
                    echo(f"Inexisting key: '{ssh_key}'. Try again.",err=True)
                    ssh_key = None

            passphrase = prompt(f"  Passphrase for {ssh_key}"
                               , default=''
                               , hide_input=True
                               , prompt_suffix=': '
                               , show_default=True
                               )
            if not confirm(f"  Continue connecting {username}@{login_node} with key {ssh_key}?"):
                raise NotConnected("Connection process ended intentionally.")
            verbose = True
             
        self.login_node = login_node
        self.username   = username

        self.ssh_key = ssh_key
        if not os.sep in self.ssh_key:
            self.ssh_key = os.path.expanduser(os.path.join('~/.ssh',ssh_key))
        
        self.label = f"{username}@{login_node}"
        if label:
            self.label+=f' ({label})'
        
        self.paramiko_client = None
        try:
            self.paramiko_client = paramiko.client.SSHClient()
            self.paramiko_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if passphrase:
                self.paramiko_client.connect( hostname     = login_node
                                            , username     = username
                                            , key_filename = self.ssh_key
                                            , passphrase   = passphrase
                                            )
            else:
                self.paramiko_client.connect( hostname     = login_node
                                            , username     = username
                                            , key_filename = self.ssh_key
                                            )
            if verbose:
                echo(f"Successfully connected: {self.label} (key='{self.ssh_key}').", err=True)
        except:
            raise NotConnected(f"Failed to connect {self.label} (key='{self.ssh_key}').")
            self.paramiko_client = None
    #---------------------------------------------------------------------------    
    def is_connected(self):
        """
        Test if the connection succeeded.
        
        :rtype: bool.
        """
        return not self.paramiko_client is None
    #---------------------------------------------------------------------------    

#===============================================================================
