# RadioSim
The HARMONI's 1D Radiometric Simulator.

![screenshot](https://user-images.githubusercontent.com/610895/208652736-4eac37bf-0430-4129-9c31-50f41d44dcf7.png)

## Getting the code
This is a work in progress. If you want to retrieve the latest changes in the project, clone directly from the development branch (`develop`) as:

```
$ git clone --branch develop git@github.com:BatchDrake/radiosim.git
$ cd radiosim
```

Or, if you have already cloned the repository, just fetch and switch the branch:

```
$ cd radiosim
$ git fetch origin develop
$ git checkout develop
$ git pull origin develop
```

## Installing dependencies
All dependencies are stored in `requirements.txt`. You can install them automatically with:

```
$ pip3 install -r requirements.txt
```

## Running
Radiosim consists of two scripts: `radiosim.py` (the CLI interface) and `qradiosim.py` (the GUI for RadioSim). You can run them with:

```
$ python3 radiosim.py
```

Or:

```
$ python3 qradiosim.py
```

Note that if you do not pass any arguments to `radiosim.py`, it  will run a simulation with default parameters. Pass `-h` to `radiosim.py` to see the list of available options:

```
$ python3 radiosim.py -h
```
