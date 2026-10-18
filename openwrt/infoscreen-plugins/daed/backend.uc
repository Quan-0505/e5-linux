'use strict';

import * as fs from 'fs';

const TOKEN_FILE = '/etc/e5-infoscreen/daed-token.json';
const PAIR_STATE = 'daed-pairing';

return function(ctx) {
	function failure(message, status) {
		return { status, type: 'application/json', body: sprintf('%J', { ok: false, error: message }) };
	}
	function service_running() {
		let ready = ctx.sh_json('/usr/bin/daed wait-ready --timeout 1s --json 2>/dev/null');
		return ready?.ok == true && ready?.ready == true;
	}
	function clean(dir) {
		for (let name in [ 'body', 'headers', 'response' ]) {
			let path = dir + '/' + name;
			if (fs.stat(path)) fs.unlink(path);
		}
		if (fs.stat(dir)) fs.rmdir(dir);
	}
	function valid_token(token) {
		return type(token) == 'string' && match(token, /^[A-Za-z0-9._~+\/=\-]{16,4096}$/);
	}
	function load_token() {
		let value = fs.readfile(TOKEN_FILE);
		if (value == null) return null;
		let saved = json(value);
		if (type(saved) != 'object' || !valid_token(saved.token) || int(saved.expiresAt ?? 0) <= time())
			return null;
		return saved;
	}
	function save_token(token) {
		let dir = '/etc/e5-infoscreen';
		if (fs.chmod(dir, 0o700) == null) return false;
		if (fs.writefile(TOKEN_FILE, sprintf('%J', { token, expiresAt: time() + 30 * 86400 }) + '\n') == null)
			return false;
		return fs.chmod(TOKEN_FILE, 0o600) != null;
	}
	function request_daed(method, path, token, body) {
		let pipe = fs.popen('mktemp -d /tmp/e5-daed-auth.XXXXXX', 'r');
		if (!pipe) return { error: '无法创建临时请求目录。' };
		let dir = pipe.read('all').trim();
		if (pipe.close() != 0 || !match(dir, /^\/tmp\/e5-daed-auth\.[A-Za-z0-9]+$/))
			return { error: '无法创建临时请求目录。' };
		if (fs.chmod(dir, 0o700) == null) { fs.rmdir(dir); return { error: '无法保护临时认证数据。' }; }
		let page_id = fs.readfile('/proc/sys/kernel/random/uuid')?.trim();
		if (!page_id || !match(page_id, /^[0-9a-f-]{36}$/i)) { clean(dir); return { error: '无法建立 daed 页面会话。' }; }
		let headers = [ 'Content-Type: application/json', 'x-daed-page-id: ' + page_id ];
		if (token) headers.push('Authorization: Bearer ' + token);
		if (fs.writefile(dir + '/headers', join('\n', headers) + '\n') == null || fs.chmod(dir + '/headers', 0o600) == null) {
			clean(dir); return { error: '无法保护临时认证数据。' };
		}
		let command = '/usr/bin/curl -sS --max-time 12 --request ' + method + ' --header @' + dir + '/headers';
		if (body != null) {
			if (fs.writefile(dir + '/body', sprintf('%J', body)) == null || fs.chmod(dir + '/body', 0o600) == null) {
				clean(dir); return { error: '无法保护临时认证数据。' };
			}
			command += ' --data-binary @' + dir + '/body';
		}
		command += ' --output ' + dir + '/response --write-out "%{http_code}" http://127.0.0.1:2023/api/' + path + ' 2>/dev/null';
		let request = fs.popen(command, 'r');
		if (!request) { clean(dir); return { error: '无法连接 daed。' }; }
		let status_text = request.read('all').trim(), exit_code = request.close(), response_text = fs.readfile(dir + '/response');
		clean(dir);
		if (exit_code != 0 || !match(status_text, /^[0-9]{3}$/) || response_text == null)
			return { error: 'daed 暂时无法响应，请稍后重试。' };
		let response = response_text == '' ? {} : json(response_text);
		if (type(response) != 'object') response = {};
		return { status: int(status_text), data: response };
	}
	function subscription_list(token) {
		let result = request_daed('GET', 'subscriptions', token, null);
		if (result.error) return { error: result.error };
		if (result.status == 401) return { error: '登录已过期，请重新扫码登录。', status: 401 };
		if (result.status < 200 || result.status >= 300 || type(result.data.items) != 'array')
			return { error: '无法读取订阅列表，请检查 daed 服务。', status: 502 };
		let items = [];
		for (let item in result.data.items) {
			if (type(item.id) != 'int' && type(item.id) != 'string') continue;
			let id = '' + item.id;
			if (!match(id, /^[0-9]{1,12}$/)) continue;
			items.push({ id, name: type(item.tag) == 'string' && item.tag != '' ? item.tag : '订阅 ' + id,
				nodeCount: int(item.nodeCount ?? 0), status: type(item.status) == 'string' ? item.status : '' });
		}
		return { subscriptions: items };
	}
	function private_ipv4(ip) {
		if (type(ip) != 'string' || !match(ip, /^(10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|192\.168\.[0-9]{1,3}\.[0-9]{1,3}|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]{1,3}\.[0-9]{1,3})$/)) return false;
		for (let part in split(ip, '.')) if (int(part) > 255) return false;
		return true;
	}
	function random_code() {
		let pipe = fs.popen('/usr/bin/openssl rand -hex 24 2>/dev/null', 'r');
		if (!pipe) return null;
		let code = pipe.read('all').trim();
		if (pipe.close() != 0 || !match(code, /^[a-f0-9]{48}$/)) return null;
		return code;
	}
	function pairing_qr() {
		let lan = ctx.ubus('network.interface.lan', 'status', {});
		let ip = lan?.['ipv4-address']?.[0]?.address;
		if (!private_ipv4(ip)) return failure('无法确认设备局域网地址。', 400);
		let code = random_code();
		if (!code) return failure('无法生成配对码。', 500);
		let url = 'https://' + ip + '/e5-daed-login/#' + code;
		let dirpipe = fs.popen('mktemp -d /tmp/e5-daed-qr.XXXXXX', 'r');
		if (!dirpipe) return failure('无法生成二维码。', 500);
		let dir = dirpipe.read('all').trim(); dirpipe.close();
		if (!match(dir, /^\/tmp\/e5-daed-qr\.[A-Za-z0-9]+$/) || fs.chmod(dir, 0o700) == null) return failure('无法生成二维码。', 500);
		fs.writefile(dir + '/url', url); fs.chmod(dir + '/url', 0o600);
		let pipe = fs.popen('/usr/bin/qrencode -t SVG -m 2 -l M -r ' + dir + '/url -o - 2>/dev/null', 'r');
		let svg = pipe ? pipe.read('all') : null;
		let ok = pipe && pipe.close() == 0 && type(svg) == 'string' && length(svg) < 32768;
		if (fs.stat(dir + '/url')) fs.unlink(dir + '/url'); fs.rmdir(dir);
		if (!ok) return failure('二维码生成失败；请连接 E5 Wi-Fi 并检查设备 HTTPS 服务。', 503);
		ctx.state_put(PAIR_STATE, { code, expires: time() + 300 });
		fs.chmod('/tmp/run/e5-infoscreen/api/plugin-daed-' + PAIR_STATE + '.json', 0o600);
		return { status: 200, type: 'application/json', body: sprintf('%J', { qrSvg: svg, expiresAt: time() + 300 }) };
	}
	return {
		'GET /status': function(req) { return { running: service_running() }; },
		'POST /pairing': function(req) { return pairing_qr(); },
		'GET /pair-status': function(req) {
			let saved = load_token();
			if (!saved) return { loggedIn: false };
			let result = subscription_list(saved.token);
			if (result.error) {
				if (result.status == 401) fs.unlink(TOKEN_FILE);
				return { loggedIn: false };
			}
			return { loggedIn: true, subscriptions: result.subscriptions };
		},
		'POST /pair-login': function(req) {
			let challenge = ctx.state_get(PAIR_STATE), code = req.body?.code;
			if (!challenge || challenge.expires < time() || code != challenge.code) return failure('配对码已失效，请在屏幕刷新二维码。', 410);
			let username = req.body?.username, password = req.body?.password;
			if (type(username) != 'string' || type(password) != 'string' || length(username) < 1 || length(username) > 128 || length(password) < 1 || length(password) > 256)
				return failure('请输入有效的账号和密码。', 400);
			let result = request_daed('POST', 'auth/token', null, { username, password });
			if (result.error) return failure(result.error, 502);
			if (result.status == 401 || result.status == 403) return failure('账号或密码不正确。', 401);
			if (result.status < 200 || result.status >= 300 || !valid_token(result.data.token)) return failure('daed 登录失败，请稍后重试。', 502);
			if (!save_token(result.data.token)) return failure('无法安全保存登录状态。', 500);
			ctx.forget(PAIR_STATE);
			return { ok: true };
		},
		'POST /logout': function(req) { if (fs.stat(TOKEN_FILE)) fs.unlink(TOKEN_FILE); return { ok: true }; },
		'GET /subscriptions': function(req) {
			let saved = load_token();
			if (!saved) return failure('请先扫码登录 daed。', 401);
			let result = subscription_list(saved.token);
			if (result.error) { if (result.status == 401 && fs.stat(TOKEN_FILE)) fs.unlink(TOKEN_FILE); return failure(result.error, result.status ?? 502); }
			return { ok: true, subscriptions: result.subscriptions };
		},
		'POST /action': function(req) {
			let action = req.body?.action;
			if (type(action) != 'string') return failure('无效操作', 400);
			if (action == 'subscriptions') {
				let saved = load_token(), id = '' + (req.body?.subscriptionId ?? '');
				if (!saved) return failure('请先扫码登录 daed。', 401);
				if (!match(id, /^[0-9]{1,12}$/)) return failure('无效的订阅项。', 400);
				let result = request_daed('POST', 'subscriptions/' + id + '/refresh', saved.token, null);
				if (result.error) return failure(result.error, 502);
				if (result.status == 401 || result.status == 403) { if (fs.stat(TOKEN_FILE)) fs.unlink(TOKEN_FILE); return failure('登录已过期，请重新扫码登录。', 401); }
				if (result.status < 200 || result.status >= 300) return failure('订阅更新失败，请在 daed 页面查看详情。', 502);
				return { ok: true, message: '订阅更新已提交。' };
			}
			if (index([ 'start', 'stop', 'reload' ], action) < 0) return failure('不支持此操作', 400);
			let running = service_running();
			if (action == 'start' && running) return { ok: true, message: 'DAED 已经运行。' };
			if (action == 'stop' && !running) return { ok: true, message: 'DAED 已经停止。' };
			if (action == 'reload' && !running) return failure('DAED 已停止，请先启动。', 409);
			let command = action == 'start' ? '/etc/init.d/daed start' : action == 'stop' ? '/etc/init.d/daed stop' : '/usr/bin/daed reload --timeout 20s --json >/dev/null 2>&1';
			if (ctx.run(command) != 0) return failure('操作失败，请检查 DAED 服务状态。', 502);
			return { ok: true, message: action == 'start' ? '已提交 DAED 启动。' : action == 'stop' ? '已提交 DAED 停止。' : 'DAED 配置重载完成。' };
		}
	};
};
