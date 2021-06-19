import micropython
import os

from microshell import help
import microshell as shell

import flairdev

micropython.alloc_emergency_exception_buf(1024)

flairdev.initialize()
flairdev.render_loop()
