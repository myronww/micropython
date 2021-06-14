
import os

shell_help_text = """
============= Shell Helpers =============
shell.cat(filename) - display the contents of a file
shell.cd(directory) - change the current working directory
shell.ls() - lists the current files
shell.tail(filename, count=10) - display the tail of a file
"""

helpfunc = help

def help(obj=None):
    if obj is not None:
        helpfunc(obj)
    else:
        helpfunc()
        print(shell_help_text)
    return

def cat(filename):
    with open(filename, 'r') as cf:
        lines = cf.read()
        print(lines)
    return

def cd(directory):
    os.chdir(directory)
    return

def ls():
    ditems = os.listdir()
    print(ditems)
    return

def tail(filename, count=10):
    with open(filename, 'r') as cf:
        lines = cf.read().splitlines()
        print(lines[-count:])
    return
