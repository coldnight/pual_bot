clean:
	find ./ -name '*.py[co]' -exec rm -f {} \;
	rm -f check.jpg wait lock

restart:
	kill `cat pid.pid`; python webqq.py && tail -f log.log

stop:
	kill `cat pid.pid`

start:
	python webqq.py
