import sys
import logging
try:
    from collections import OrderedDict
except Exception:
    from ordereddict import OrderedDict
import requests
import json
import jinja2
import jinja2.meta
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


# Default iTop object to use for Action instances if no 'itop' argument is given.
ITOP_INSTANCE = None

# List of loaded factories
LOADED_FACTORIES = {}


def render_template(template, variables={}):
    """Render a Jinja2 template.

    Arguments:
        template (str): Template path.
        variables (dict, optional): Template arguments.
    """
    logger = logging.getLogger("soc.apiclient.itop.render_template")
    # Load template source.
    logger.info("loading template from '{0}'".format(template))
    with open(template, 'r') as fd:
        tpl_source = fd.read()
        # Validate that all variables used in templates are defined.
        logger.info("validating template")
        env = jinja2.Environment()
        ast = env.parse(tpl_source)
        missing = [v for v in jinja2.meta.find_undeclared_variables(ast) if v not in variables]
        if len(missing) > 0:
            raise Exception("Missing template variables: {0}".format(", ".join(missing)))
        # Render template.
        logger.info("rendering template")
        tpl = jinja2.Template(tpl_source)
        return tpl.render(**variables)


def parse_vars(vars):
    """Parse the user-provided list of templates variables.

    Format MUST be 'key:value' (quotes are optional).

    Arguments:
        vars (list of str): Template variables list.
    """
    variables = {}
    for kv in vars:
        try:
            splitted = kv.split(':')
            k = splitted[0]
            v = "".join(splitted[1:])
            # k, v = kv.split(':')
            if k is not None and len(k) > 0 and v is not None and len(v) > 0:
                variables[k] = v
            else:
                raise Exception
        except Exception:
            print("invalid variable '{0}': format is key:value".format(kv))
            sys.exit(1)
    return variables


def keys_to_dict(keys):
    """Convert dotted strings (a.b.c) to a `dict` object.
    """
    key = {}
    # Build flat K-V structure.
    for kv in keys:
        # Split key path / value tuple.
        path, raw_value = kv.split('=')
        values = raw_value.split(':')
        # Extract type / value tuple.
        if len(values) == 1:
            vtype = str
            value = values[0]
        else:
            vtype = values[0]
            value = values[1]
        # Build key.
        k = key
        for p in path.split('.')[0:-1]:
            if p not in k:
                k[p] = dict()
            k = k[p]
        k[path.split('.')[-1]] = value
    return key


def notify_mail(subject, payload, recipients=[], cc=[], sender="", server="127.0.0.1", port=25):
    """Send a mail.
    """
    logger = logging.getLogger("soc.apiclient.itop.notify_mail")
    # Builds mail.
    logger.info("setting-up mail context (subject='{subject}', sender='{sender}', recipients='{recipients}', cc='{cc}')".format(
        subject=subject,
        sender=sender,
        recipients=recipients,
        cc=cc
    ))
    email = MIMEMultipart()
    email["Subject"] = subject
    email["from"] = sender
    email["To"] = ", ".join(recipients)
    email["CC"] = ", ".join(cc)
    # Mail content.
    logger.info("setting-up mail payload (type='html')")
    email.attach(MIMEText(payload, "html"))
    # Sending mail.
    if len(recipients) > 0:
        logger.info("setting-up smtp client (host='{server}', port='{port}')".format(server=server, port=port))
        smtp_client = smtplib.SMTP(host=server, port=port)
        logger.info("sending mail")
        errors = smtp_client.sendmail(sender, recipients + cc, email.as_string())
        if len(errors) > 0:
            logger.error("error while sending mail: {errs}".format(errs=", ".join(errors)))
        else:
            logger.info("mail sent")
            logger.debug(payload)
        smtp_client.quit()
    else:
        logger.warning("mail not sent: no recipients")


class ITop(object):
    def __init__(self, config=None, **kwargs):
        self.logger = logging.getLogger("soc.apiclient.itop.ITop")
        # Extract configuration.
        if config is not None:
            self.logger.info("reading configuration from '{0}'".format(config))
            with open(config, 'r') as fd:
                self.__config = json.load(fd)
        else:
            self.__config = {}
        # Build configuration.
        missing = []
        for v in ["address", "version", "user", "password"]:
            if v in kwargs:
                self.__config[v] = kwargs[v]
            if v not in self.__config:
                missing.append(v)
        # Check configuration.
        if len(missing) > 0:
            raise Exception("Missing parameters (neither in config nor arguments): {0}".format(", ".join(missing)))
        # Prepare future calls.
        self.logger.info("setting-up requests session (warning: SSL warnings disabled !)")
        self.session = requests.Session()
        requests.packages.urllib3.disable_warnings()
        self.query_url = "{0}/webservices/rest.php?version={1}".format(self.__config["address"], self.__config["version"])
        setattr(sys.modules[__name__], "ITOP_INSTANCE", self)

    def query(self, payload):
        try:
            self.logger.info("querying (address='{0}', operation='{1}')".format(self.query_url, payload.get("operation", None)))
            self.logger.info("payload: {0}".format(json.dumps(payload)))
            response = self.session.post(self.query_url, verify=False, data={
                "auth_user": self.__config["user"],
                "auth_pwd": self.__config["password"],
                "json_data": json.dumps(payload)
            })
            return response.json()
        except Exception as error:
            raise


class Action(object):
    def __init__(self, operation=None, iclass=None, output="*", fields=None, key=None, stimulus=None, itop=None, required=[], calculated=[]):
        """Initialize the clss instance.

        Arguments:
            operation (str, optional): iTop operation (ex: 'core/get')
            iclass (str, optional): iTop object class name (ex: 'Person')
            output (str, list, optional): Query output (default to all fields - slow and memory consuming !)
            fields (dict, optional): iTop object values (used by write operations)
            key (str, int, dict, optional): iTop object key (used by search operations)
            stimulus (str, optional): Stimulus code.
            itop (object, optional): ITop object instance. Default to global instance.
            required (list of tuple of string, optional): Required `key` or `fields` values.
            calculated (list of tuple(str, callable)): Calculated outputs.
        """
        self.logger = logging.getLogger("soc.apiclient.itop.{0}".format(self.__class__.__name__))
        self.operation = operation
        self.iclass = iclass
        self.output = output
        self.fields = fields
        self.key = key
        self.stimulus = stimulus
        self.itop = itop
        self.required = required
        self.calculated = calculated

    def json_data(self):
        """Generate iTop query payload and validate the query logic.
        """
        # Base payload.
        jsdata = {
            "operation": self.operation,
            "comment": "",
        }
        # Setup class.
        if self.iclass is not None:
            jsdata["class"] = self.iclass
        # Setup output fields.
        if type(self.output) in [list, set]:
            jsdata["output_fields"] = ", ".join(self.output)
        # Setup key.
        if self.key is not None:
            if type(self.key) in [dict, OrderedDict]:
                jsdata["key"] = {}
                for k, v in self.key.items():
                    if isinstance(k, str) and type(v) in [str, int, float, dict]:
                        jsdata["key"][k] = v
                    else:
                        raise Exception("Unsupported type in [key]: key={0}, value={1} (key must be 'str', value must be 'str', 'int', 'float' or 'dict')".format(type(k), type(v)))
            elif type(self.key) in [int, str]:
                jsdata["key"] = self.key
            else:
                raise Exception("Unsupported type for [key]: {0} (expected one of 'str', 'int', 'dict')".format(type(self.key)))
        # Setup fields.
        if self.fields is not None:
            if self.operation in ["core/create", "core/update", "core/apply_stimulus"]:
                jsdata["fields"] = self.fields
            else:
                raise Exception("Cannot include the section [fields] in operation '{0}'".format(self.operation))
        # Setup stimulus
        if self.stimulus is not None:
            if self.operation in ["core/apply_stimulus"]:
                jsdata["stimulus"] = self.stimulus
            else:
                raise Exception("Cannot include the field [stimulus] in operation '{0}'".format(self.operation))
        # Done.
        return jsdata

    def __call__(self, key=None, fields=None, output=None, stimulus=None):
        """Excecute the iTop query.

        Arguments:
            key (str, int, dict, optional): Key attribute override.
            fields (dict, optional): Fields attribute override.
        """
        itop = self.itop is not None and itop or ITOP_INSTANCE
        if itop is None:
            raise Exception("Action and inherited class requires a valid ITop instance")
        # Update key and fields at run-time.
        for arg, attr in [(key, "key"), (fields, "fields"), (output, "output"), (stimulus, "stimulus")]:
            if arg is not None:
                if type(arg) in [dict, OrderedDict] and type(getattr(self, attr)) in [dict, OrderedDict]:
                    getattr(self, attr).update(arg)
                else:
                    setattr(self, attr, arg)
        # Run query.
        return itop.query(self.json_data())
        # js = itop.query(self.json_data())
        # for name, obj in js.get("objects", {}).items():
        #     obj["__calculated__"] = {}
        #     for c in self.calculated:
        #         c_name, c_func = c
        #         obj["__calculated__"][c_name] = c_func(obj)
        # return js



class ListAction(Action):
    def __init__(self):
        super(ListAction, self).__init__(operation="list_operations")


class GetAction(Action):
    def __init__(self, iclass, key=None, output="*", required=[], calculated=[]):
        if key is None:
            key = "SELECT {0}".format(iclass)
        super(GetAction, self).__init__(operation="core/get",
                                        iclass=iclass,
                                        key=key,
                                        output=output,
                                        calculated=calculated)


class CreateAction(Action):
    def __init__(self, iclass, fields={}, output="*", required=[], calculated=[]):
        super(CreateAction, self).__init__(operation="core/create",
                                           iclass=iclass,
                                           fields=fields,
                                           output=output,
                                           calculated=calculated)


class UpdateAction(Action):
    def __init__(self, iclass, key=None, fields={}, output="*", required=[], calculated=[]):
        super(UpdateAction, self).__init__(operation="core/update",
                                           iclass=iclass,
                                           key=key,
                                           fields=fields,
                                           output=output,
                                           calculated=calculated)


class StimulateAction(Action):
    def __init__(self, iclass, stimulus, fields={}, output="*", required=[], calculated=[]):
        super(StimulateAction, self).__init__(operation="core/apply_stimulus",
                                              iclass=iclass,
                                              stimulus=stimulus,
                                              fields=fields,
                                              output=output,
                                              calculated=calculated)
