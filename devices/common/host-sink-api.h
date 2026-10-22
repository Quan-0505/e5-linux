/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef SPRD_HOST_SINK_H
#define SPRD_HOST_SINK_H
struct device_node;
struct usb_phy;
bool sprd_typec_host_sink(struct device_node *node);
bool sprd_typec_external_power(struct device_node *node);
void sprd_typec_data_host(struct device_node *node, bool host);
void sprd_hsphy_external_host(struct usb_phy *phy, bool external);
bool sprd_hsphy_external_power(struct usb_phy *phy);
#endif
