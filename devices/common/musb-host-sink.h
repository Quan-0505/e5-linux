/* SPDX-License-Identifier: GPL-2.0-only */
/* Manual external 5V mode; CC stays sink and never fabricates a host event. */
static bool sprd_external_policy(struct sprd_glue *glue)
{
	struct device_node *node = of_parse_phandle(glue->dev->of_node, "extcon", 1);
	bool enabled = node && sprd_typec_host_sink(node);
	of_node_put(node);
	return enabled;
}

static void sprd_external_data_role(struct sprd_glue *glue, bool host)
{
	struct device_node *node = of_parse_phandle(glue->dev->of_node, "extcon", 1);
	if (node)
		sprd_typec_data_host(node, host);
	of_node_put(node);
}

static bool sprd_external_ready(struct sprd_glue *glue)
{
	return sprd_external_policy(glue) && glue->external_vbus &&
	       extcon_get_state(glue->external_vbus, EXTCON_USB) > 0 &&
	       extcon_get_state(glue->edev, EXTCON_USB) > 0 &&
	       glue->xceiv->chg_state == USB_CHARGER_PRESENT &&
	       (READ_ONCE(glue->xceiv->flags) & CHARGER_DETECT_DONE);
}

static int sprd_external_power_notify(struct notifier_block *nb,
				    unsigned long event, void *data)
{
	struct sprd_glue *glue = container_of(nb, struct sprd_glue, external_nb);
	if (!READ_ONCE(glue->external_stopped) &&
	    (sprd_external_policy(glue) || READ_ONCE(glue->external_host)))
		queue_work(glue->musb_wq, &glue->resume_work);
	return NOTIFY_OK;
}

static int sprd_external_charger_notify(struct notifier_block *nb,
				      unsigned long event, void *data)
{
	struct sprd_glue *glue = container_of(nb, struct sprd_glue, external_charger_nb);
	if (!READ_ONCE(glue->external_stopped) &&
	    (sprd_external_policy(glue) || READ_ONCE(glue->external_host)))
		queue_work(glue->musb_wq, &glue->resume_work);
	return NOTIFY_OK;
}

static void sprd_external_stop(void *data)
{
	struct sprd_glue *glue = data;
	WRITE_ONCE(glue->external_stopped, true);
	if (glue->external_charger_registered) {
		usb_unregister_notifier(glue->xceiv, &glue->external_charger_nb);
		glue->external_charger_registered = false;
	}
	if (glue->external_registered) {
		extcon_unregister_notifier(glue->external_vbus, EXTCON_USB, &glue->external_nb);
		glue->external_registered = false;
	}
}

static int sprd_external_start(struct sprd_glue *glue)
{
	struct device_node *node = of_parse_phandle(glue->dev->of_node, "extcon", 1);
	struct platform_device *typec;
	int ret;
	if (!node)
		return -ENODEV;
	typec = of_find_device_by_node(node);
	of_node_put(node);
	if (!typec)
		return -EPROBE_DEFER;
	/* The Type-C provider's first extcon is the actual VBUS GPIO. */
	glue->external_vbus = extcon_get_edev_by_phandle(&typec->dev, 0);
	put_device(&typec->dev);
	if (IS_ERR(glue->external_vbus))
		return PTR_ERR(glue->external_vbus);
	glue->external_nb.notifier_call = sprd_external_power_notify;
	ret = extcon_register_notifier(glue->external_vbus, EXTCON_USB, &glue->external_nb);
	if (ret)
		return ret;
	glue->external_registered = true;
	glue->external_charger_nb.notifier_call = sprd_external_charger_notify;
	ret = usb_register_notifier(glue->xceiv, &glue->external_charger_nb);
	if (ret) {
		sprd_external_stop(glue);
		return ret;
	}
	glue->external_charger_registered = true;
	return devm_add_action_or_reset(glue->dev, sprd_external_stop, glue);
}
