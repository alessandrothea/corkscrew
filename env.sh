HERE=$( cd $(dirname $BASH_SOURCE)/ && pwd)
echo $HERE

export PATH="$HERE/scripts:$PATH"
export PYTHONPATH="$HERE/python:$PYTHONPATH"
