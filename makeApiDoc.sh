#!/bin/sh
# Generate API documentation from Python sources with the Epydoc tool

cd $(dirname $0)

epydoc --help > /dev/null
if [ $? -eq 0 ]; then
    epydoc --html -o api --name="Pology" .
else
    echo "Epydoc not found. Please install it from Epydoc website : http://epydoc.sf.net"
    echo "or use your distribution package (apt-get install python-epydoc or yum install epydoc)"
    exit 1
fi
