"""
Class CommandBase
=================
Base class for all command classes.
"""
#===============================================================================
from click import echo
#===============================================================================
from time import sleep
import lrcmd.exceptions
#===============================================================================
class CommandBase:
    """
    Base class for RemoteCommand and LocalCommand. 
    Derived classes typically reimplement or augmentCommandBase.__init__() 
    and execute(self,post_processor=None)
    """
    #---------------------------------------------------------------------------
    def __init__(self,command,connection=None,working_directory=None):
        """
        :param connection: either a Connection, or an object with a connection member.
        """
        self.command = command
        if not connection is None:
            raise ValueError(f"Connection argument must not be specified on a LocalCommand object.")
        self.connection = None
        self.working_directory = working_directory
    #---------------------------------------------------------------------------
    def maximum_wait_time(self,attempts=6,wait=60):
        """
        Compute the maximum wait time before the command gives up.
        """
        return ( 2**(attempts-1) -1 )*wait
    #---------------------------------------------------------------------------
    def __repeat_message(self,msg='',verbose=False):
        if msg:
            msg += '\n'
            if verbose:
                echo(msg, err=True)
            self.repeat_messages += msg
        else:
            self.repeat_messages = '' 
    #---------------------------------------------------------------------------
    def execute_repeat(self,attempts=6,wait=60,check=True,stderr_is_error=False,error_log=None, post_processor=None,verbose=False,timeout=None):
        """
        Repeated execution after failure.
        
        :param int attempts: number of times the command is retried on failure, before it gives up. 
        :param int wait: seconds of wait time after the first failure, doubled on every failure.
        :param post_processor: a function the transforms the output (on stdout) of the command.
        :param bool verbose: print error message to stderr if the command fails.
        
        :return: on success the output (on stdout) of the command as processed by *post_processor*, otherwise *None*
          
        If the command fails, retry it after <wait> seconds. The total number 
        of attempts is <attempts>. After every attempt, the wait time is doubled.
        
        =============== === === === === ==== ====
        attempt          1   2   3   4    5   6  
        wait time        0   1   2   4    8   16
        total wait time  0   1   3   7   15   31 
        =============== === === === === ==== ====
        
        The maximum wait time is ( 2**(attempts-1) -1 )*wait and can be obtained by
        method :func:`CommandBase.maximum_wait_time`.
        
        The default retries times, waiting at most 31 minutes. (This does not 
        include the time the command is being executed).
        
        If the repeated excution of the command fails, the accumulated error messages 
        are found in the class variable :class:`self.repeat_messages`. 
        
        This command is inherited by derived classes.
        """
        self.repeat_messages = ''
        
        attempts_left = attempts
        sleep_time = wait
        slept_time = 0
        self.__repeat_message()
        while attempts_left:
            try:
                self.result = self.execute( post_processor=post_processor
                                          , check=check
                                          , stderr_is_error=stderr_is_error
                                          , error_log=error_log
                                          , timeout=timeout
                                          )
                self.__repeat_message(f"Attempt {attempts-attempts_left+1}/{attempts} succeeded after {slept_time} seconds.",verbose=verbose)
                self.result.repeat_messages = self.repeat_messages
                self.result.attempts = attempts-attempts_left+1
                return self.result
            except Exception as e:
                attempts_left -= 1
                self.__repeat_message(f"Attempt {attempts-attempts_left}/{attempts} failed." \
                                      f"\n  {type(e).__name__}: {e}"                               \
                                      f"\n  Retrying after {sleep_time} seconds."
                                     ,verbose=verbose
                                     )
                if attempts_left:
                    sleep(wait)
                    slept_time += sleep_time 
                    sleep_time *=2
    
        else:
            assert attempts_left==0
            self.__repeat_message(f"Exhausted after {attempts} attempts.",verbose=verbose)
            raise lrcmd.exceptions.RepeatedExecutionFailed('\n'+self.repeat_messages)
        
        assert False # should never happen
    #---------------------------------------------------------------------------
    def __repr__(self):
        """
        """
        if isinstance(self.command,list):
            cmd = ' '.join(self.command)
        else:
            cmd = self.command
        r =  f"< {self.__class__}: '{cmd}'"
        if self.connection is None:
            r += +' >'
        else:
            r += f', {self.connection.label} >'
        return r
    #---------------------------------------------------------------------------
    def __str__(self):
        """
        Convert the command to a str and return it.
        """
        if isinstance(self.command,list):
            return ' '.join(self.command)
        else:
            return self.command
    #---------------------------------------------------------------------------
    def process_output(self, post_processor=None
                           , check=True,stderr_is_error=False
                           , error_log=None
                           ):
        """
        Check for output on stderr and whether this is considered an error,
        and call the post_processor.
        """
        if check:
            if self.result.returncode!=0:
                msg = f"\n  {type(self).__name__} '{self.command}'\n  yields nonzero exit code: {self.result.returncode}\n  stderr: {self.result.stderr}"
                raise lrcmd.exceptions.NonZeroReturnCode(msg, result=self.result, error_log=error_log)
        
        if stderr_is_error:
            if self.result.stderr:
                msg = f"\n  {type(self).__name__} '{self.command}'\n  yields output on stderr: \n{self.result.stderr}"
                raise lrcmd.exceptions.Stderr(msg, result=self.result, error_log=error_log)

        if not post_processor is None:
            self.result.processed = post_processor(self.result.stdout)
            
        return self.result
    #---------------------------------------------------------------------------
            
#===============================================================================

