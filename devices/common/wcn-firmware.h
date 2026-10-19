/* SPDX-License-Identifier: GPL-2.0-only */
/* T512N stock wcn_bsp.ko (512NCA05): f08c XPE read, 132e4..1330c image
 * selection. These registers enable reading eFuse; no programming operation.
 * Called under the existing serialized WCN power/download path.
 */
#define WCN_XPE_PACK_BYTES 0x300000U
#define WCN_XPE_IMAGE_OFFSET 0x180000U
#define WCN_XPE_IMAGE_BYTES 0xe73b0U

static int wcn_xpe_fuse = -1;

static int wcn_xpe_set_read_bit(u32 address, u32 mask)
{
	u32 value;
	int ret;

	ret = sprdwcn_bus_reg_read(address, &value, sizeof(value));
	if (ret < 0)
		return ret;
	if (value & mask)
		return 0;
	value |= mask;
	return sprdwcn_bus_reg_write(address, &value, sizeof(value));
}

static int wcn_read_xpe_fuse(void)
{
	static const struct { u32 address, mask; } prepare[] = {
		{ 0x4083c32c, BIT(22) },
		{ 0x4083c024, BIT(11) },
		{ 0x4083c050, BIT(18) },
		{ 0x40858040, BIT(0) },
	};
	u32 value;
	int i, ret;

	if (wcn_xpe_fuse >= 0)
		return wcn_xpe_fuse;
	for (i = 0; i < ARRAY_SIZE(prepare); i++) {
		ret = wcn_xpe_set_read_bit(prepare[i].address, prepare[i].mask);
		if (ret < 0)
			return ret;
	}
	ret = sprdwcn_bus_reg_read(0x40859030, &value, sizeof(value));
	if (ret < 0)
		return ret;
	wcn_xpe_fuse = (value >> 29) & 3;
	return wcn_xpe_fuse;
}

static int wcn_select_firmware(bool marlin3lite, const u8 *data, size_t size,
			       const u8 **selected, size_t *selected_size)
{
	int xpe;

	*selected = data;
	*selected_size = size;
	/* Only the verified raw 3 MiB Marlin3Lite concatenation has this layout.
	 * Other chips and standalone images keep their existing download path.
	 */
	if (!marlin3lite || size != WCN_XPE_PACK_BYTES)
		return 0;
	xpe = wcn_read_xpe_fuse();
	if (xpe < 0)
		return xpe;
	if (xpe != 1)
		return 0;
	if (WCN_XPE_IMAGE_OFFSET > size ||
	    WCN_XPE_IMAGE_BYTES > size - WCN_XPE_IMAGE_OFFSET)
		return -EINVAL;
	*selected = data + WCN_XPE_IMAGE_OFFSET;
	*selected_size = WCN_XPE_IMAGE_BYTES;
	pr_info("WCN XPE=%d: firmware offset=%#x length=%#x\n", xpe,
		WCN_XPE_IMAGE_OFFSET, WCN_XPE_IMAGE_BYTES);
	return 0;
}
