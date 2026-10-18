import { snapshot, text } from './read.uc';

export function profile(root) {
    root = root ?? '';
    // Board stagers enable this service only for the battery-powered profiles.
    return text(root + '/etc/e5/device-profile') ? {} : null;
};

export function sample(root) {
    root = root ?? '/sys/class/power_supply';
    // charger-manager already owns voltage qualification and charging exceptions.
    return snapshot(root, ['battery']);
};
