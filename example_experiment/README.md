# GLADOS CLI Example Experiment

This directory includes an example experiment (the "add_nums.py" and "manifest.yml" files), as well as a "template_manifest.yml" file that further explains some of the fields required of the manifest file.

To run an experiment with the CLI, it is required that the experiment program have the same compatibility as what is normally submitted via the GLADOS web app (described [here](https://automatingsciencepipeline.github.io/Monorepo/tutorial/usage/)).

Additionally, it is required that there is a manifest.yml in the same directory as the CLI that describes the attributes of the experiment normally defined in the information, parameters, and constants tabs. The fields required in this file are outlined in the "template_manifest.yml" file.

To run this experiment, move the manifest.yml file to the same directory as glados_cli.py, and run the command

```sh
python glados_cli.py -z example_experiment/add_nums.py
```
