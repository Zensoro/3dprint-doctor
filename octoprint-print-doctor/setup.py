#!/usr/bin/env python3
from setuptools import setup

plugin_name = "OctoPrint-PrintDoctor"
plugin_identifier = "print_doctor"
plugin_version = "0.1.0"
plugin_description = "Real-time print defect monitoring using Print Doctor"
plugin_author = "Zensoro"
plugin_license = "MIT"
plugin_homepage = "https://github.com/Zensoro/3dprint-doctor"

plugin_requires = ["print-doctor>=0.5.0", "opencv-python-headless>=4.6", "requests>=2.20"]

setup(
    name=plugin_name,
    version=plugin_version,
    description=plugin_description,
    author=plugin_author,
    license=plugin_license,
    url=plugin_homepage,
    packages=["octoprint_print_doctor"],
    include_package_data=True,
    entry_points={
        "octoprint.plugin": [
            f"{plugin_identifier} = octoprint_print_doctor",
        ],
    },
    install_requires=plugin_requires,
)
