from setuptools import setup, find_packages


setup(name="soc_apiclient_itop",
      version="1.0.0",
      description="iTop client API",
      author="Jean-Philippe Clipffel",
      packages=["soc", "soc.apiclient", "soc.apiclient.itop", "soc.apiclient.itop.factories"],
      namespace_packages = ["soc", "soc.apiclient", ],
      entry_points={"console_scripts": ["soc.apiclient.itop=soc.apiclient.itop.__main__:main", ]},
      install_requires=["requests", "tabulate", "jinja2"],
      include_package_data=True
)
