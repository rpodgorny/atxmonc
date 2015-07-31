import time
import requests
import subprocess
import json
import re
import jinja2
import threading
import random
import logging


SEND_INTERVAL = 20
THREADS_MAX = 10


def logging_setup(level, fn=None):
	logger = logging.getLogger()
	logger.setLevel(logging.DEBUG)

	formatter = logging.Formatter('%(levelname)s: %(message)s')
	sh = logging.StreamHandler()
	sh.setLevel(level)
	sh.setFormatter(formatter)
	logger.addHandler(sh)

	if fn:
		formatter = logging.Formatter('%(asctime)s: %(levelname)s: %(message)s')
		fh = logging.FileHandler(fn)
		fh.setLevel(level)
		fh.setFormatter(formatter)
		logger.addHandler(fh)
	#endif
#enddef

def load_probes(fn):
	ret = []

	with open(fn, 'r') as f:
		t = jinja2.Template(f.read())
		rendered = t.render()
	#endwith

	for line in rendered.splitlines():
		line = line.strip()

		if not line: continue
		if line.startswith('#'): continue

		interval, probe, *args = line.split(';')
		if interval.endswith('m'):
			interval = float(interval[:-1]) * 60
		else:
			interval = float(interval)
		#endif

		ret.append((interval, probe, args))
	#endfor

	return ret
#enddef


def probe_alive():
	return {'ok': 1}
#enddef


def probe_load():
	if not sys.platform.startswith('linux'):
		return None
	#endif

	ret = {}

	with open('/proc/loadavg', 'r') as f:
		loads = [float(i) for i in f.read().split()[:3]]
		ret['1min'] = loads[0]
		ret['5min'] = loads[1]
		ret['15min'] = loads[2]
	#endwith

	return ret
#enddef


def probe_ping(host, ipv6=False):
	if ipv6:
		cmd = 'ping6 -c 5 -q %s 2>/dev/null' % host
	else:
		cmd = 'ping -c 5 -q %s 2>/dev/null' % host
	#endif

	try:
		out = subprocess.check_output(cmd, shell=True).decode()
	except:
		return {'ok': 0}
	#endtry

	packet_loss = None
	rtt_avg = None
	for line in out.splitlines():
		if 'packet loss' in line:
			# TODO: compile this?
			m = re.match('.+, (\d+)% packet loss,.+', line)
			packet_loss = int(m.groups()[0])
		#endif

		if 'rtt min/avg/max/mdev' in line:
			# TODO: compile this?
			m = re.match('rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms', line)
			_, rtt_avg, _, _ = [float(i) for i in m.groups()]
		#endif
	#endfor

	return {'ok': 1, 'packet_loss': packet_loss, 'rtt_avg': rtt_avg}
#enddef


def probe_ping6(host):
	return probe_ping(host, ipv6=True)
#enddef


def probe_iperf3(host):
	ret = {}
	ok = 1

	for direction in ['up', 'down']:
		if direction == 'down':
			cmd = 'timeout 20 iperf3 -c %s -J -R -P 5' % host
		else:
			cmd = 'timeout 20 iperf3 -c %s -J -P 5' % host
		#endif

		try:
			out = subprocess.check_output(cmd, shell=True).decode()
			res = json.loads(out)
			bits_per_second = res['end']['sum_received']['bits_per_second']
			ret['%s/bits_per_second' % direction] = bits_per_second
		except:
			ok = 0
		#endtry
	#endfor

	ret['ok'] = ok
	return ret
#enddef


def probe_url_contains(url, contains=None):
	r = requests.get(url)

	if contains in r.text:
		ok = 1
	else:
		ok = 0
	#endif

	return {'ok': ok}
#enddef


def send(url, data):
	requests.post(url, data=json.dumps(data))
#enddef


class ProbeThread(threading.Thread):
	def __init__(self, interval, fn, *args):
		threading.Thread.__init__(self)

		self.interval = interval
		self.fn = fn
		self.args = args
		self.res = None
	#enddef

	def run(self):
		self.res = self.fn(*self.args)
	#enddef
#endclass


PROBE_MAP = {
	'alive': probe_alive,
	'load': probe_load,
	'ping': probe_ping,
	'ping6': probe_ping6,
	'url_contains': probe_url_contains,
	'iperf3': probe_iperf3,
}

def expand_host(s):
	if not '[' in s or not '-' in s or not ']' in s: return [s, ]

	pre = s.split('[')[0]
	post = s.split(']')[1]

	from_ = s.split('[')[1].split('-')[0]
	to_ = s.split(']')[0].split('-')[1]
	from_ = int(from_)
	to_ = int(to_)

	ret = []
	for i in range(from_, to_ + 1):
		ret.append('%s%s%s' % (pre, i, post))
	#endfor

	return ret
#enddef

def run(url, probes_fn, host):
	url = '%s/save' % url  # TODO: not very nice

	data = []
	last_sent = 0

	src = host
	probes = load_probes(probes_fn)

	threads = {}

	last_run = {}
	for interval, probe, args in probes:
		# TODO: cut-n-pasted to below
		probe_name = '%s/%s' % (src, probe)
		if args:
			probe_name = '%s/%s' % (probe_name, '/'.join(args))
		#endif

		last_run[probe_name] = time.time() - interval * random.random()
	#endfor

	while 1:
		t = time.time()

		for probe_name, thr in threads.copy().items():
			if thr.is_alive(): continue

			res = thr.res
			interval = thr.interval

			if res is not None:
				for res_name, v in res.items():
					k_full = '%s/%s' % (probe_name, res_name)
					data.append({'path': k_full, 'value': v, 'time': t, 'interval': interval})
					logging.debug('got %s=%s' % (k_full, v))
				#endfor
			#endif

			thr.join()
			del threads[probe_name]
		#endfor

		for interval, probe, args in probes:
			# TODO: cut-n-pasted from above
			probe_name = '%s/%s' % (src, probe)
			if args:
				probe_name = '%s/%s' % (probe_name, '/'.join(args))
			#endif

			if t < last_run[probe_name] + interval: continue
			if len(threads) >= THREADS_MAX: break

			logging.debug('starting %s (%s/%s)' % (probe_name, len(threads) + 1, THREADS_MAX))

			fn = PROBE_MAP[probe]
			thr = ProbeThread(interval, fn, *args)
			thr.start()
			threads[probe_name] = thr
			last_run[probe_name] = t
		#endfor

		if data and t > last_sent + SEND_INTERVAL:
			logging.debug('sending %d records' % len(data))
			try:
				send(url, data)
				data = []
				last_sent = t
			except Exception as e:
				print('failed to send data: %s -> %s' % (str(e), len(data)))
			#endtry
		#endif

		time.sleep(1)  # TODO: hard-coded shit
	#endwhile
#enddef