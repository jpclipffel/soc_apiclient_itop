import os
import sys
import logging
import json
try:
    import importlib
except Exception:
    pass
import argparse
import glob
from . import notify_mail, ITop, ListAction, GetAction, CreateAction, LOADED_FACTORIES


# Logging globals.
logger = logging.getLogger("soc.apiclient.itop")
logger.propagate = False
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())
itop = None
loaded_factories = {}


# Hardcoded error notification mail.
error_mail = """
<html>
    <body>
        <h1 style="color:Tomato;">soc.apiclient.itop error</h1>
        <br>
        {err}
    </body>
</html>
"""


def load_factories():
    """Load all available factories at once.
    """
    facts_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "factories", "*.py")
    logger.info("locating all factories from '{0}'".format(facts_path))
    for factory_path in [f for f in glob.glob(facts_path)]:
        factory_name = os.path.basename(factory_path).split(".py")[0]
        if factory_name not in ["__init__", ]:
            logger.info("loading factory '{0}' from '{1}'".format(factory_name, factory_path))
            try:
                LOADED_FACTORIES[factory_name] = importlib.machinery.SourceFileLoader("factories.{0}".format(factory_name), factory_path).load_module()
            except Exception:
                LOADED_FACTORIES[factory_name] = __import__("soc.apiclient.itop.factories.{0}".format(factory_name), fromlist=["soc.apiclient.itop.factories"])


def main():
    # Load loaded_factories.
    load_factories()
    # Arguments parser.
    parser = argparse.ArgumentParser(description="SOC client API for iTop")
    # Globals arguments.
    parser.add_argument("--config", type=str, help="iTOP API configuration file")
    parser.add_argument("--logfile", type=str, default=None, help="Log file path")
    parser.add_argument("--notify-mail", dest="notify_mail", action="store_true", help="Send a mail notification is case of error")
    parser.add_argument("--mail-server", type=str, dest="mail_server", default="127.0.0.1", help="Mail server for error notification")
    parser.add_argument("--mail-recipients", type=str, dest="mail_recipients", default=["soc@excellium-services.com", "jpclipffel@excellium-services.com"], nargs='+', help="Mail recipients")
    # Commands sub-parsers.
    sp = parser.add_subparsers(dest="command", help="Command")
    sp.required = True
    # Factories parsers.
    for name, factory in LOADED_FACTORIES.items():
        if getattr(factory, "add_parser", None) is not None:
            factory.add_parser(sp)
    # Parse arguments.
    args = parser.parse_args()
    # Logging.
    if args.logfile is not None:
        logger.addHandler(logging.handlers.RotatingFileHandler(args.logfile, mode='a', maxBytes=1000000, backupCount=0))
    logformatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    for handler in logger.handlers:
        handler.setFormatter(logformatter)
    # Execution.
    try:
        # Connect iTop.
        itop = ITop(config=args.config)
        # Run command.
        args.func(args)
    except Exception as error:
        logger.error(str(error))
        logger.exception(error)
        if args.notify_mail is True:
            notify_mail(subject="soc.apiclient.itop error",
                        payload=error_mail.format(err=str(error)),
                        server=args.mail_server,
                        recipients=args.mail_recipients)
        raise error


if __name__ == "__main__":
    main()
