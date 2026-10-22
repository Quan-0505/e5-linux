/* SPDX-License-Identifier: GPL-2.0-only */
static ssize_t usb_role_show(struct device *dev,
		struct device_attribute *attr, char *buf)
{
	struct sc27xx_typec *sc = dev_get_drvdata(dev);
	struct device_node *node;
	struct usb_role_switch *sw;
	enum usb_role role;
	if (!sc) return -EAGAIN;
	/* Report the controller, not an inferred role from the power attachment. */
	for_each_compatible_node(node, NULL, "snps,sprd-dwc3") {
		if (!of_device_is_available(node))
			continue;
		sw = usb_role_switch_find_by_fwnode(of_fwnode_handle(node));
		if (IS_ERR_OR_NULL(sw))
			continue;
		role = usb_role_switch_get_role(sw);
		usb_role_switch_put(sw);
		of_node_put(node);
		return sysfs_emit(buf, "%s\n", role == USB_ROLE_HOST ? "host" :
			role == USB_ROLE_DEVICE && sc->partner_connected ? "device" : "none");
	}
	return sysfs_emit(buf, "none\n");
}
static DEVICE_ATTR_RO(usb_role);

