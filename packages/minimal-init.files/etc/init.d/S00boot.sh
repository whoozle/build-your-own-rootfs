#!/bin/sh

echo "mounting /tmp"
mount -t tmpfs tmp /tmp
echo "mounting /dev"
mount -t devtmpfs dev /dev
echo "mounting /proc"
mount -t proc proc /proc
echo "mounting /sys"
mount -t sysfs sysfs /sys
echo "switching to mdev"
echo /sbin/mdev > /proc/sys/kernel/hotplug
echo "populating devices from sysfs"
mdev -s
echo "boot done"
