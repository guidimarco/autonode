"""
Entry point: run the multi-agent workflow (coder → reviewer).
Wires infrastructure (CrewFactory, ToolRegistry) to the application use case.
"""

from autonode.presentation.cli import main

if __name__ == "__main__":
    main()
