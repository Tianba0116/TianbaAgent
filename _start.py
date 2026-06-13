"""TianbaAgent start script."""
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.argv.append("--dual")

from cli.utils import run_dual_foreground
run_dual_foreground()
