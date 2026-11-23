const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../location_control.py'), 'utf8');
const script = source.match(/js="""([\s\S]*?)"""/)[1]
    .replace('export default function', 'function render');
function setup(transit = true, blocked = false) {
    const button = {}, status = {}, order = [], positions = [];
    let success, failure, url;
    const tab = {closed: false, document: {body: {}},
        close() {this.closed = true;},
        location: {replace(value) {url = value; order.push('navigate');}}};
    const context = {URL, window: {isSecureContext: true,
        open(target, frame) {
            assert.equal(target, 'about:blank'); assert.equal(frame, '_blank');
            order.push('open'); return blocked ? null : tab;
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
        success: () => success({coords: {latitude: 37.474, longitude: 127.095}}),
        failure: () => failure({code: 1}), url: () => url};
}
let state = setup();
assert.deepEqual(state.order, ['open', 'gps']);
assert.equal(state.tab.opener, null);
state.success();
const query = new URL(state.url()).searchParams;
assert.equal(query.get('slat'), '37.474');
assert.equal(query.get('slng'), '127.095');
assert.equal(query.get('elng'), '127.1');
assert.equal(query.get('elat'), '37.5');
state.cleanup();
assert.equal(state.tab.closed, false, 'Do not close the delivered Naver tab');
state = setup(true, true);
assert.deepEqual(state.order, ['open']);
assert.match(state.status.textContent, /pop-ups/);
state = setup(); state.failure();
assert.equal(state.tab.closed, true);
assert.equal(state.url(), undefined);
state = setup(); state.cleanup(); state.success();
assert.equal(state.tab.closed, true);
assert.equal(state.url(), undefined);
state = setup(false); state.success();
assert.deepEqual(state.order, ['gps']);
assert.equal(state.positions.length, 1);
console.log('Transit new-tab navigation, coordinates, blocked popups, GPS failure, cleanup and walking passed.');
