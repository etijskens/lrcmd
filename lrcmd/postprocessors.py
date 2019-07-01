"""
Processing the output of a command
==================================

Here is a collection of functions to process the output (on stdout) of a 
command. These functions are typically used by specifying the *postprocessor* 
option of the generic *run* function or the *execute* method of *LocalCommand*,
or *RemoteCommand*.
"""
#===============================================================================
try:
    import xmltodict
except ImportError:
    xmltodict = None
#===============================================================================
def xml_to_odict(s):
    """
    A post-processor function that parses a string *s*, containing the xml 
    output of a command into an OrderedDict using :func:`xmltodict.parse`.
     
    :rtype: OrderedDict
    """
    if xmltodict is None:
        msg = "Warning: lore.postprocessors:\n  Module xmltodict is not available."\
              "\n  If you need to parse xml output from a command, either install "\
              "\n  xmltodict (using pip, conda), or activate a Python environment" \
              "\n  which has xmltodict installed."
        raise ImportError(msg)
    return xmltodict.parse(s)
#===============================================================================
def list_of_lines(s):
    """
    A post-processor function that splits a string *s* (the stdout output of a)
    command in a list of lines (newlines are removed).
    
    :rtype: a list of lines (str)
    """
    return s.split('\n')
#===============================================================================
def list_of_non_empty_lines(s):
    """
    A post-processor function that splits a string with the output of a command 
    in a list of non-empty lines (newlines and empty lines are removed).
    
    :rtype: a list of non-empty lines (str)
    """
    lines = list_of_lines(s)
    nonempty_lines = []
    for line in lines:
        if line:
            nonempty_lines.append(line)
    return nonempty_lines
#===============================================================================