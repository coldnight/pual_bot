clean:
	find ./ -name '*.py[co]' -exec rm -f {} \;
	rm -f check.jpg

restart:
	kill `cat pid.pid`; python webqq.py && tail -f log.log
