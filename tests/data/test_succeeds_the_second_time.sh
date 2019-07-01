#!/bin/bash

if [ -d newdir ]; then
	rc=0
else
	mkdir newdir
	rc=1
fi
exit ${rc}