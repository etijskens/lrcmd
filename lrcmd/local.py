"""
Class LocalCommand
==================
Command class for executing local commands.
"""
#===============================================================================
import logging
lrcmd_log = logging.getLogger('lrcmd_log')
#===============================================================================
import shlex,subprocess
from types import SimpleNamespace
#===============================================================================
from lrcmd.core       import CommandBase
from lrcmd.exceptions import CommandTimedOut
#===============================================================================
class LocalCommand(CommandBase):
    """
    Class for execution local system commands, using 
    `subprocess <https://docs.python.org/3/library/subprocess.html>`_ . 
    
    :param str command: the command as you would type it on a terminal. 
    :param str working_directory: the command will be executed in directory 
        *working_directory*
    :param int timeout: raise *CommandTimedOut* when the command does not 
        finish after *timeout* seconds.
    """
    def __init__(self,command,working_directory=None):
        super().__init__(command,working_directory=working_directory)
        if isinstance(self.command,str):
            self.command = shlex.split(self.command)
        else:
            raise TypeError('Expecting "str" for command.')
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
            written, nor None.
            
        :return: on success the output (on stdout) of the command as processed 
            by *post_processor*, otherwise an exception is raised.

        :raise: *NonZeroReturnCode*, *Stderr*, *CommandTimedOut*
        """
        self.result = SimpleNamespace()
        try:
            self.result = subprocess.run( self.command
                                        , capture_output=True
                                        , timeout=timeout
                                        , check=False
                                        , cwd=self.working_directory
                                        , encoding='utf-8'
                                        )
        except subprocess.TimeoutExpired:
            msg = f"Local command '{self.command}' timed out after {timeout}s."
            raise CommandTimedOut(msg, result=self.result, error_log=error_log)
            

        self.process_output( post_processor=post_processor
                           , check=check, stderr_is_error=stderr_is_error
                           , error_log=error_log
                           )
        
        return self.result
    #---------------------------------------------------------------------------

#===============================================================================    
