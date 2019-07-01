"""
Exceptions 
==========
Exceptions used by lore.
"""
#===============================================================================
class FailedCommand(Exception):
    """
    Base class for lore exceptions.
    
    The common functionality is that they all store the result of the command 
    in self.result. This comprises the output on stdout, stderr and the return
    code.
    """
    def __init__(self, *args, result=None, error_log=None, **kwargs ):
        super().__init__(*args,**kwargs)
        self.result = result
        if error_log:
            error_log.error(str(self))
#===============================================================================
class Stderr(FailedCommand):
    """
    This exception is raised if executing a command produces output on stderr 
    (and the stderr_is_error parameter was set to True).
    """
    pass
#===============================================================================
class NonZeroReturnCode(FailedCommand):
    """
    This exception is raised if executing a command produces a nonzero return 
    code (and the check parameter was set to True).
     """
    pass
#===============================================================================
class RepeatedExecutionFailed(FailedCommand):
    """
    This exception is raised if execute_repeat on a command did not succeed 
    after the maximum number of attempts. The criterion for success depends on 
    the check and stderr_is_error parameters.
    """
    pass
#===============================================================================
class CommandTimedOut(FailedCommand):
    """
    This exception is raised if a command was executed with a timeout, and the 
    command did not complete in time. 
    """
    pass
#===============================================================================
class NotConnected(Exception):
    """
    This exception is raised if no ssh connection (paramiko) could be 
    established.
    """
    pass
#===============================================================================
