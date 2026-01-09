"""
Docstring for main
"""
import sys
from src.cli import VerityDemoCLI


if __name__ == "__main__":
    v = VerityDemoCLI()
    #v.handle_create_account()
    #v.handle_create_diddoc()
    #v.register_diddoc()
    #main()
    sys.path.append('.')
    # Simulate CLI arguments for headless mode
    #sys.argv = ['cli.py', '--message',
    #            'Test claim', '--issuer', 'did:verity:gov:demo-election-comm', "--store"]
    try:
        v.run()
        #main()
    except SystemExit:
        pass
