"""
Class RemoteCommand
===================
Command class for executing remote commands.
"""
#===============================================================================
import shlex
from types import SimpleNamespace
#===============================================================================
import paramiko
#===============================================================================
from lrcmd.core       import CommandBase
from lrcmd.exceptions import CommandTimedOut
#===============================================================================
class RemoteCommand(CommandBase):
    """
    Command that is executed remotely (on a login-node) using 
    `paramiko.client <http://docs.paramiko.org/en/2.4/api/client.html>`_ .
    """                
    def __init__(self, connection, command,working_directory=None):
        """
        :param str command: the command as you would type it on a terminal.
        :param Connection connection: a valid Connection object.
        :param str working_directory: if not None, *command* is executed in 
            directory *working_directory*. This is achieve by prepending *command* 
            with ``'cd <working_directory> && '``. 
        """
        super().__init__(command, working_directory=working_directory)
        
#         assert isinstance(connection, Connection)
        self.connection = connection
        
        if self.working_directory:
            self.command = f'cd {shlex.quote(self.working_directory)} && {self.command}'
    #---------------------------------------------------------------------------
    def execute(self, post_processor=None
                    , check=True, stderr_is_error=False, timeout=None
                    , error_log=None
                    ):
        """
        Execute the command.
        
        :param post_processor: a function the transforms the output (on stdout) 
            of the command.
        :param bool check: if True, and the command yields a nonzero return code, 
            raises NonZeroReturnCode. 
        :param bool stderr_is_error: if True, output on stderr is considered an 
            error, and a Stderr is raised. 
        :param int timeout: a positive integer indicating that the command must 
            complete in *timeout* seconds. If not, a CommandTimedOut exception
            is raised. If timeout is None, the command may take for ever to 
            complete.
        :param bool error_log: a logger object to which error messages are 
            written, or None.
        :return: on success a types.SimpleNamespace object containing the *stdout*
            (optionally post-processed by *postprocessor*),
            *stderr*, and *returncode*, as produced by the command. 

        :raise: *NonZeroReturnCode*, *Stderr*, *CommandTimedOut* if the command 
            failed.
        """
        self.result = SimpleNamespace()
        try:
            tpl = self.connection.paramiko_client.exec_command(self.command,timeout=timeout)
            self.result.stdout = tpl[1].read().decode('utf-8')
            self.result.stderr = tpl[2].read().decode('utf-8')
            self.result.returncode = tpl[1].channel.recv_exit_status()
        except paramiko.channel.socket.timeout:
            msg = f"Remote command '{self.command}' timed out after {timeout}s.\n  on {self.connection.label}"
            raise CommandTimedOut(msg, error_log=error_log)

        return self.process_output( check=check
                                  , stderr_is_error=stderr_is_error
                                  , error_log=error_log
                                  , post_processor=post_processor
                                  )
    #---------------------------------------------------------------------------
    
