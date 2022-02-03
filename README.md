# SOC / API Client / iTop

`soc_apiclient_itop` is a Python package (3+) designed to interact
with an iTOP (2+) server through its REST/JSON API.

## Installation

It is **highly recommended** to install the tool within a virtual environment.

### Dependencies

* `python3+`: Python interpreter in version 3 or newer
* `pip`: Python package manager

### Virtual environment

* Install `virtualenv` on the target system if needed: `pip3 install virtualenv`
* Create a virtual environment: `python3 -m virtualenv <path/to/your/venv>`
* Activate the virtual environment: `source <path/to/your/venv>/bin/activate`

### Install the package

If you wish to keep the package up-to-date with a GIT repository:

* Clone the repository: run `git clone https://smc.tld/soc_apiclient_itop.git`
* Install the package: run `pip3 install -e soc_apiclient_itop/`

Otherwise:

* Install the package: run `pip3 install soc_apiclient_itop/`


## Basic usage

### CLI usage

```shell
soc.apiclient.itop [-h]
                   --config <path/to/config.json>
                   [--logfile <path/to/logfile>]
                   <command> [command arguments]
```

Arguments:

* `-h`: Show help.
* `--config`: Path to iTop API configuration file. Mandatory.
* `--logfile`: Path to logfile. Optional (will log to *stdout* by default).
* `command`: Command to execute.

### Configuration file

The package uses a JSON configuration file, which requires the following attributes:

```json
{
  "address": "https://itop.tld",
  "version": "1.3",
  "user": "your_username",
  "password": "your_password"
}
```


## Factories

### SIEM Incident (`incident-siem.py`)

This factory provides the following controls:

* `incident-siem-get`: List existing SIEM incidents
* `incident-siem-exists`: Check if a given incident exists
* `incident-siem-publog`: Add a public log to an existing SIEM incident
* `incident-siem-create`: Create or update a SIEM incident
* `incident-siem-resolve`: Set an existing incident to *Resolved* status

#### Examples call

##### Create or update an incident

```shell
soc.apiclient.itop \
--config conf/soc_apiclient_itop.json \
--mail-server 172.16.253.88 \
\
incident-siem-create \
--inc_title "SOC-EXC-SIEM-011" \
--inc-urgency 1 \
--org-code EXC
--text "This this a new comment"
--vars \
  source_ip:"1.2.3.4" \
  signatures:"sig1,sig2,sig3,sig4" \
  dest_ip:"4.3.2.1" \
  time:"now" \
  username:"Someone" \
  comment:"Analyst comment here" \
  case_name:"SOC-EXC-SIEM-011"
```

## For developers

`soc_apiclient_itop` is built around *factories*, *parser* and *actions*.

### Actions

The base package defines the standard actions `ListAction`, `GetAction`,
`CreateAction`, `UpdateAction` and `StimulateAction`.
Those actions may be used to read, write and update raw iTop objects.

### Parser

The base package implements a simple parser which is extended by the available factories.
The parsers exposes the available *commands* (where a command is usually a wrapper around one ore more *actions*)

### Factory

A factory a simple Python module which defines custom *parser* and *actions*.
Factories are dynamically loaded during the tool invocation.

#### Example: Get action

First, import the required modules:

```python
import ITop, GetAction
```

Create an iTop connection:

```python
itop = ITop(config="./soc_apiclient_itop.cfg.json")
```

Create an `get` factory on the selected iTop class (ex: `Person`):

```python
persons = GetAction(iclass="Person", output=["first_name", "name", "email"])
```

The following arguments are required:

* `iclass`: The iTop class name

The following arguments are optional but highly recommended:

* `output`: The list of fields to extract from iTop

Optional arguments for a `get` action:

* `key`: Object ID (`int`), search query (`str`) or search structure (`dict`)

Query all `Person` objects (only if no `key` has been defined in the factory):

```python
everybody = persons()
```

Search for one or more `Person` through an OQL query:

```python
someone = persons(key="SELECT Person WHERE name LIKE 'A_Person_Name'")
```

Search for one or more `Person` through a property tree:

```python
someone = persons(key={
  "name": "A_Person_Name",
  "email": "someone@mail.com"
  })
```

Search for a single `Person` through the object `id`:

```python
someone = persons(key=1234)
```
