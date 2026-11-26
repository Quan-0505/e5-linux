'use strict';
'require view';

return view.extend({
    render: function() {
        var target = new URL(window.location.href);
        target.protocol = 'http:';
        target.port = '2023';
        target.username = ''; target.password = '';
        target.pathname = '/'; target.search = ''; target.hash = '';

        var frame = E('iframe', {
            'title': 'DAED 管理控制台',
            'src': target.href,
            'style': 'display:block;width:100%;height:calc(100dvh - 220px);min-height:560px;border:1px solid var(--border-color,#d0d5dd);border-radius:8px;background:#fff;'
        });
        var controls = E('div', {
            'style': 'display:flex;flex-wrap:wrap;align-items:center;gap:12px;margin:0 0 16px;'
        }, [
            E('a', { 'class': 'cbi-button cbi-button-action', 'href': target.href,
                'target': '_blank', 'rel': 'noopener noreferrer' }, '在新标签页打开 DAED'),
            E('button', { 'class': 'cbi-button', 'type': 'button', 'click': function() {
                frame.src = target.href;
            } }, '刷新内嵌页面')
        ]);
        var children = [ E('h2', {}, 'DAED'), controls ];
        if (window.location.protocol === 'https:') {
            children.push(E('p', { 'class': 'alert-message warning' },
                '当前 LuCI 使用 HTTPS，浏览器会阻止嵌入 HTTP 控制台，请使用上方按钮在新标签页打开 DAED。'));
        } else {
            children.push(frame);
        }
        return E('div', { 'class': 'daed-embedded-console' }, children);
    },
    handleSave: null, handleSaveApply: null, handleReset: null
});
