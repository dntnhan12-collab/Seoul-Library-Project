const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../location_control.py'), 'utf8');
const script = source.match(/js="""([\s\S]*?)"""/)[1].replace('export default function', 'function render');
function setup(transit = true, blocked = false) {
    const button = {}, status = {}, order = [], positions = [];
    let success, failure, url;
    const tab = {};
    const context = {URL, window: {isSecureContext: true,
        open(target, frame) {
            assert.notEqual(target, 'about:blank'); assert.equal(frame, '_blank');
            url = target; order.push('open'); return blocked ? null : tab;
        }}, navigator: {geolocation: {getCurrentPosition(ok, error) {
            order.push('gps'); success = ok; failure = error;
        }}}};
    vm.createContext(context);
    vm.runInContext(script, context);
    const cleanup = context.render({
        parentElement: {querySelector(selector) {return selector === 'button' ? button : status;}},
        data: {browser_url: transit ? 'https://map.naver.com/index.nhn?elng=127.1&elat=37.5&etext=Library' : null},
        setTriggerValue(name, position) {positions.push(position);},
    });
    button.onclick();
    return {button, status, order, positions, tab, cleanup,
        unblock: () => {blocked = false;},
        success: (latitude = 37.474) => success({coords: {latitude, longitude: 127.095}}),
        failure: () => failure({code: 1}), url: () => url};
}
let state = setup();
assert.deepEqual(state.order, ['gps'], 'No blank tab while awaiting permission');
state.success();
assert.deepEqual(state.order, ['gps', 'open']);
assert.equal(state.tab.opener, null);
const query = new URL(state.url()).searchParams;
assert.equal(query.get('slat'), '37.474');
assert.equal(query.get('slng'), '127.095');
assert.equal(query.get('elng'), '127.1');
assert.equal(query.get('elat'), '37.5');
assert.equal(state.positions.length, 1);
state = setup(true, true); state.success();
assert.equal(state.button.textContent, 'Open directions');
assert.equal(state.positions.length, 0);
state.unblock(); state.button.onclick();
assert.deepEqual(state.order, ['gps', 'open', 'open'], 'Retry opens the prepared route without requesting GPS again');
assert.equal(state.positions.length, 1);
assert.equal(state.button.textContent, 'Find route from my location');
state = setup(); state.failure();
assert.equal(state.url(), undefined);
assert.equal(state.button.disabled, false);
state = setup(); state.cleanup(); state.success();
assert.equal(state.url(), undefined);
state = setup(); state.success(0);
assert.equal(state.url(), undefined);
state = setup(false); state.success();
assert.deepEqual(state.order, ['gps']);
assert.equal(state.positions.length, 1);
console.log('No blank tabs, preserved endpoints, popup retry, GPS failure, cleanup and walking passed.');
