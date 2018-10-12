"""
Just great logging.
"""
import logging


def configure(verbose=False,
              logformat='%(asctime)s - %(name)s - %(levelname)s - %(message)s'):
    """
    Configure how our logging should behave, and return the logging object
    for pure convenience.
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format=logformat)
    else:
        logging.basicConfig(level=logging.INFO, format=logformat)
        logging.getLogger('requests.packages.urllib3.connectionpool'
                          ).setLevel(logging.WARNING)
    return logging
