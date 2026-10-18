'use strict';

return function(ctx) {
	function service_running() {
		let ready = ctx.sh_json('/usr/bin/daed wait-ready --timeout 1s --json 2>/dev/null');
		return ready?.ok == true && ready?.ready == true;
	}
	function failure(message, status) {
		return { status, type: 'application/json', body: sprintf('%J', { ok: false, error: message }) };
	}
	return {
		'GET /status': function(req) {
			return { running: service_running() };
		},
		'POST /action': function(req) {
			let action = req.body?.action;
			if (type(action) != 'string') return failure('无效操作', 400);
			if (action == 'subscriptions')
				return failure('订阅更新需要 daed 账号验证；当前版本没有本地免登录接口。', 501);
			if (index([ 'start', 'stop', 'reload' ], action) < 0)
				return failure('不支持此操作', 400);
			let running = service_running();
			if (action == 'start' && running) return { ok: true, message: '代理服务已经运行。' };
			if (action == 'stop' && !running) return { ok: true, message: '代理服务已经停止。' };
			if (action == 'reload' && !running) return failure('代理服务已停止，请先启动。', 409);
			let command = action == 'start' ? '/etc/init.d/daed start' :
				action == 'stop' ? '/etc/init.d/daed stop' :
				'/usr/bin/daed reload --timeout 20s --json >/dev/null 2>&1';
			if (ctx.run(command) != 0) return failure('操作失败，请检查 daed 服务状态。', 502);
			return { ok: true, message: action == 'start' ? '已提交启动。' :
				action == 'stop' ? '已提交停止。' : '配置重载完成。' };
		}
	};
};
