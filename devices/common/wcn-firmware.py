#!/usr/bin/env python3
"""Select the stock Marlin3Lite XPE image without altering device firmware files."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
RELATIVE = Path('drivers/unisoc_platform/sprdwcn/platform/wcn_boot.c')
MARKER = '#include "wcn-firmware.h"'


def apply(kernel):
    path = Path(kernel) / RELATIVE
    text = path.read_text()
    start = text.index('static int btwifi_download_firmware(void)\n{')
    end = text.index('\nstatic int wcn_get_syscon_regmap(', start)
    original = text[start:end]
    if MARKER not in text:
        def replace(old, new):
            nonlocal original
            if original.count(old) != 1:
                raise ValueError('Unexpected WCN firmware downloader: ' + old[:70])
            original = original.replace(old, new, 1)

        replace('\tchar *tx_img_ptr = NULL;',
                '\tchar *tx_img_ptr = NULL;\n\tstruct wcn_match_data *match_config;\n'
                '\tconst u8 *download_data;\n\tsize_t download_size;')
        replace('\tpimghdr = (struct sys_img_header *)(firmware->data);', '''
	/* Validate before touching the header, including signed-image lengths. */
	if (firmware->size < sizeof(sec_img_magic) || firmware->size > INT_MAX) {
		err = -EINVAL;
		goto out;
	}
	pimghdr = (struct sys_img_header *)(firmware->data);''')
        replace('\t\tif (pimghdr->img_real_size == 0 ||\n'
                '\t\t\t(pimghdr->img_signed_size <=\n'
                '\t\t\t(SEC_IMAGE_HDR_SIZE + pimghdr->img_real_size)) ||\n'
                '\t\t\tpimghdr->img_signed_size > firmware->size) {', '''		if (firmware->size < SEC_IMAGE_HDR_SIZE ||
			pimghdr->img_real_size == 0 ||
			pimghdr->img_signed_size <= SEC_IMAGE_HDR_SIZE ||
			pimghdr->img_signed_size > firmware->size ||
			pimghdr->img_real_size >=
			pimghdr->img_signed_size - SEC_IMAGE_HDR_SIZE) {''')
        # The short-circuit condition above must precede all header field reads.
        replace('\tcount = (tx_img_size + PACKET_SIZE - 1) / PACKET_SIZE;', '''	match_config = get_wcn_match_config();
	err = wcn_select_firmware(match_config && match_config->unisoc_wcn_m3lite,
				 (const u8 *)tx_img_ptr, tx_img_size,
				 &download_data, &download_size);
	if (err)
		goto out;
	count = DIV_ROUND_UP(download_size, PACKET_SIZE);''')
        replace('(tx_img_size - len) > PACKET_SIZE ?', '(download_size - len) > PACKET_SIZE ?')
        replace('PACKET_SIZE : (tx_img_size - len);', 'PACKET_SIZE : (download_size - len);')
        replace('memcpy(buf, tx_img_ptr + len, trans_size);',
                'memcpy(buf, download_data + len, trans_size);')
        replace('''		if (err < 0) {
			pr_err("marlin dt write %s error:%d\\n", __func__, err);
			release_firmware(firmware);
			return err;
		}''', '''		if (err < 0) {
			pr_err("marlin dt write %s error:%d\\n", __func__, err);
			goto out;
		}''')
        replace('''	release_firmware(firmware);
	pr_info("marlin %s successfully!\\n", __func__);

	if (sec_img_magic == SEC_IMAGE_MAGIC && tx_img_ptr)
		vfree(tx_img_ptr);

	return 0;''', '''	err = 0;
	pr_info("marlin %s successfully!\\n", __func__);
out:
	/* tx_img_ptr always owns the allocation, never the selected interior. */
	if (tx_img_ptr && tx_img_ptr != (char *)firmware->data)
		vfree(tx_img_ptr);
	release_firmware(firmware);
	return err;''')
        text = text[:start] + MARKER + '\n\n' + original + text[end:]
    else:
        for required in ('wcn_select_firmware(', 'goto out;', 'download_data + len'):
            if required not in original:
                raise ValueError('Incomplete WCN firmware adaptation: ' + required)
    path.write_text(text)
    (path.parent / 'wcn-firmware.h').write_bytes((HERE / 'wcn-firmware.h').read_bytes())


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kernel', type=Path)
    apply(parser.parse_args().kernel)
