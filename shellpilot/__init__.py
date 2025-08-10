"""
ShellPilot-AI-powered System Administration

A CLI tool that wraps Linux commands with Large Language Models,
providing intelligent system administration capabilities.
"""
__version__ = "0.1.0"
__author__ = "Raghav Yadav"
__email__ = "raghavyadav1734@gmail.com"
__description__="AI-powered Linux system Administration CLI"


from shellpilot.config import Config

__all__={
    "__version__",
    "__author__",
    "__email__",
    "__description__",
    "LLMProvider",
    "CommandExecutor",
    "config"
}