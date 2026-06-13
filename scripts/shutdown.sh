#!/bin/bash

#Stop service
cd `dirname $0`/..
export BASE_DIR=`pwd`
pid=`ps ax | grep -i app.py | grep "${BASE_DIR}" | grep python3 | grep -v grep | awk '{print $1}'`
if [ -z "$pid" ] ; then
        echo "No TianbaAgent running."
        exit -1;
fi

echo "TianbaAgent(${pid}) is running..."

kill ${pid}

echo "Send shutdown request to TianbaAgent(${pid}) OK"