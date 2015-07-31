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
