'use strict';
'require view';
return view.extend({
    render: function() {
        var target = new URL(window.location.href);
        target.protocol = 'http:';
        target.port = '2023';
        target.username = ''; target.password = '';
        target.pathname = '/'; target.search = ''; target.hash = '';
        window.location.replace(target.href);
        return E('p', {}, '正在打开daed管理界面…');
    },
    handleSave: null, handleSaveApply: null, handleReset: null
});
