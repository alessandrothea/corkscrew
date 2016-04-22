set sourced=($_)

set HERE=`dirname $sourced[2]`
set HERE=`cd $HERE && pwd`

echo $HERE

setenv PATH "$HERE/scripts:$PATH"
setenv PYTHONPATH "$HERE/python:$PYTHONPATH"


