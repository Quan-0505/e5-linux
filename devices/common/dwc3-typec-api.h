/* SPDX-License-Identifier: GPL-2.0-only */
bool sprd_dualpower_typec_host_sink(struct device_node *node)
{
	struct platform_device *pdev = of_find_device_by_node(node);
	struct sc27xx_typec *sc;
	bool enabled = false;

	if (!pdev)
		return false;
	sc = platform_get_drvdata(pdev);
	if (sc)
		enabled = READ_ONCE(sc->external_host_policy);
	put_device(&pdev->dev);
	return enabled;
}
EXPORT_SYMBOL_GPL(sprd_dualpower_typec_host_sink);

void sprd_dualpower_typec_data_role(struct device_node *node, bool host)
{
	struct platform_device *pdev = of_find_device_by_node(node);
	struct sc27xx_typec *sc;

	if (!pdev)
		return;
	sc = platform_get_drvdata(pdev);
	if (sc && sc->port && READ_ONCE(sc->partner_connected))
		typec_set_data_role(sc->port, host ? TYPEC_HOST : TYPEC_DEVICE);
	put_device(&pdev->dev);
}
EXPORT_SYMBOL_GPL(sprd_dualpower_typec_data_role);
