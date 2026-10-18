#!/usr/bin/env python3
"""SC2355 management-frame channel and station-event bounds (MU300 b5a7bc55)."""
from pathlib import Path


def apply(kernel):
    base = Path(kernel) / 'drivers/unisoc_platform/sprd_wlan_combo'
    edits = {
        'common/cfg80211.c': (
            '\t*cookie = ++mgmt_index;',
            '''	/* No frequency is required for an AP's on-channel management frame. */
	if (!chan) {
		if (params->offchan ||
		    (wdev->iftype != NL80211_IFTYPE_AP && wdev->iftype != NL80211_IFTYPE_P2P_GO))
			return -EINVAL;
#if (LINUX_VERSION_CODE >= KERNEL_VERSION(5, 15, 0))
		if (wdev->valid_links || params->link_id > 0)
			return -EINVAL;
		chan = wdev->links[0].ap.chandef.chan;
#else
		chan = wdev->chandef.chan;
#endif
		if (!chan)
			return -ENODATA;
	}

	*cookie = ++mgmt_index;'''),
        'sc2355/cmdevt.c': (
            '''	sprd_report_softap(vif, sta->is_connect, sta->mac, sta->ie,
			   sta->ie_len);''',
            '''	/* A leave needs only the flag/MAC; a join must contain all its IEs. */
	u16 ie_len;

	if (len < sizeof(sta->is_connect) + sizeof(sta->mac))
		return;
	if (!sta->is_connect) {
		sprd_report_softap(vif, 0, sta->mac, NULL, 0);
		return;
	}
	if (len < sizeof(*sta))
		return;
	ie_len = le16_to_cpu(sta->ie_len);
	if (ie_len > len - sizeof(*sta))
		return;
	sprd_report_softap(vif, sta->is_connect, sta->mac, sta->ie, ie_len);'''),
    }
    changed = {}
    for name, (old, new) in edits.items():
        text = (base / name).read_text()
        if new in text:
            continue
        if text.count(old) != 1:
            raise ValueError('Unexpected SC2355 event source: ' + name)
        changed[name] = text.replace(old, new, 1)
    for name, text in changed.items():
        (base / name).write_text(text)


if __name__ == '__main__':
    import sys
    apply(sys.argv[1])
