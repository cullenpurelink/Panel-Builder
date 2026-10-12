/* ------------------------------------------------------------
   Shared local-machine runtime shim for the PureLink module suite.
   Every module includes this as its FIRST <script> tag:
     <script src="../shared/local-db.js"></script>
   before its own app script. It defines window.claude.use(name)
   with the same shape Claude's hosted db/user/downloads
   capabilities have, so a module's own code needs no changes to
   run standalone:
     db.collection(name).onSnapshot/orderBy/limit/doc(id).set/delete/get
     db.doc('a/b').onSnapshot/set
     user.id/name/can/isOwner/profiles/search
     downloads.save({filename, data})

   Storage: one IndexedDB database ("purelink-local-db"), one
   object store ("kv") keyed by "<collection>/<docId>", so a new
   module introducing a new collection name is just a new key
   prefix — no schema/version migration needed.

   Library-action undo/redo: every set()/delete() on the
   "layouts" or "approvals" collections is tracked (last 10) and
   surfaced as a small floating pill (bottom-right) with an
   Undo/Redo button, independent of any module's own UI.

   Data lives only in this browser, on this machine.
------------------------------------------------------------ */
(function () {
  if (window.claude) return;              // a real host already provided it
  if (!window.indexedDB) return;          // no IndexedDB support: degrade like "no capabilities"

  var DB_NAME = 'purelink-local-db';
  var STORE = 'kv';
  var dbPromise = null;

  function openDb() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise(function (resolve, reject) {
      var req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = function () {
        var idb = req.result;
        if (!idb.objectStoreNames.contains(STORE)) idb.createObjectStore(STORE);
      };
      req.onsuccess = function () { resolve(req.result); };
      req.onerror = function () { reject(req.error); };
    });
    return dbPromise;
  }
  function key(coll, id) { return coll + '/' + id; }

  function idbGet(coll, id) {
    return openDb().then(function (idb) {
      return new Promise(function (resolve, reject) {
        var tx = idb.transaction(STORE, 'readonly');
        var req = tx.objectStore(STORE).get(key(coll, id));
        req.onsuccess = function () { resolve(req.result); };
        req.onerror = function () { reject(req.error); };
      });
    });
  }
  function idbSet(coll, id, value) {
    return openDb().then(function (idb) {
      return new Promise(function (resolve, reject) {
        var tx = idb.transaction(STORE, 'readwrite');
        tx.objectStore(STORE).put(value, key(coll, id));
        tx.oncomplete = function () { resolve(); };
        tx.onerror = function () { reject(tx.error); };
      });
    });
  }
  function idbDelete(coll, id) {
    return openDb().then(function (idb) {
      return new Promise(function (resolve, reject) {
        var tx = idb.transaction(STORE, 'readwrite');
        tx.objectStore(STORE).delete(key(coll, id));
        tx.oncomplete = function () { resolve(); };
        tx.onerror = function () { reject(tx.error); };
      });
    });
  }
  function idbScan(coll) {
    return openDb().then(function (idb) {
      var lower = coll + '/', upper = coll + '/￿';
      return new Promise(function (resolve, reject) {
        var tx = idb.transaction(STORE, 'readonly');
        var range = IDBKeyRange.bound(lower, upper, false, false);
        var req = tx.objectStore(STORE).openCursor(range);
        var out = [];
        req.onsuccess = function (e) {
          var cursor = e.target.result;
          if (cursor) {
            out.push({ id: String(cursor.key).slice(lower.length), value: cursor.value });
            cursor.continue();
          } else resolve(out);
        };
        req.onerror = function () { reject(req.error); };
      });
    });
  }

  /* ---------- live listeners ---------- */
  var listeners = {}; // collection name -> [{fire}]
  function notify(coll) {
    (listeners[coll] || []).slice().forEach(function (entry) { entry.fire(); });
  }
  function addListener(coll, fire) {
    var entry = { fire: fire };
    (listeners[coll] = listeners[coll] || []).push(entry);
    setTimeout(fire, 0);
    return function unsubscribe() {
      listeners[coll] = (listeners[coll] || []).filter(function (e) { return e !== entry; });
    };
  }

  /* ---------- library-action undo/redo ---------- */
  var TRACKED = { layouts: true, approvals: true };
  var MAX_HISTORY = 10;
  var undoStack = [], redoStack = [];
  var widgetTimer = null;

  function labelFor(coll, id, prev, next, op) {
    var name = (next && next.name) || (prev && prev.name) || id;
    if (coll === 'layouts') {
      if (op === 'delete') return 'Deleted "' + name + '" from the library';
      return prev ? 'Updated "' + name + '" in the library' : 'Saved "' + name + '" to the library';
    }
    if (coll === 'approvals') {
      if (op === 'delete') return 'Removed the approval record for "' + name + '"';
      var status = next && next.status;
      if (status === 'released') return 'Released "' + name + '"';
      if (status === 'approved') return 'Approved "' + name + '"';
      if (status === 'draft') return 'Returned "' + name + '" to draft';
      return 'Updated the approval for "' + name + '"';
    }
    return 'Changed "' + name + '"';
  }

  function ensureWidget() {
    var el = document.getElementById('pbUndoPill');
    if (el) return el;
    el = document.createElement('div');
    el.id = 'pbUndoPill';
    el.style.cssText = 'position:fixed;right:16px;bottom:calc(16px + env(safe-area-inset-bottom,0px));'
      + 'background:#16191D;color:#F8F8F9;font:13px/1.4 "Segoe UI",system-ui,-apple-system,sans-serif;'
      + 'padding:9px 10px 9px 14px;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,.35);'
      + 'display:flex;align-items:center;gap:10px;z-index:99999;opacity:0;pointer-events:none;'
      + 'transition:opacity .15s;max-width:calc(100vw - 32px)';
    var span = document.createElement('span');
    span.id = 'pbUndoPillText';
    var btn = document.createElement('button');
    btn.id = 'pbUndoPillBtn';
    btn.type = 'button';
    btn.style.cssText = 'background:#5B8DF2;color:#0B1020;border:none;border-radius:6px;'
      + 'padding:5px 10px;font:600 13px inherit;cursor:pointer;white-space:nowrap';
    el.appendChild(span);
    el.appendChild(btn);
    (document.body || document.documentElement).appendChild(el);
    return el;
  }
  function showWidget(text, btnText, onClick) {
    var el = ensureWidget();
    el.querySelector('#pbUndoPillText').textContent = text;
    var btn = el.querySelector('#pbUndoPillBtn');
    btn.textContent = btnText;
    btn.onclick = onClick;
    el.style.opacity = '1';
    el.style.pointerEvents = 'auto';
    clearTimeout(widgetTimer);
    widgetTimer = setTimeout(function () {
      el.style.opacity = '0';
      el.style.pointerEvents = 'none';
    }, 8000);
  }

  function restoreValue(entry, which) {
    var value = which === 'prev' ? entry.prevValue : entry.newValue;
    var p = value === undefined ? idbDelete(entry.collection, entry.id) : idbSet(entry.collection, entry.id, value);
    return p.then(function () { notify(entry.collection); });
  }
  function undoLast() {
    var entry = undoStack.pop();
    if (!entry) return Promise.resolve();
    return restoreValue(entry, 'prev').then(function () {
      redoStack.push(entry);
      showWidget('Undone: ' + entry.label, 'Redo', redoLast);
    });
  }
  function redoLast() {
    var entry = redoStack.pop();
    if (!entry) return Promise.resolve();
    return restoreValue(entry, 'new').then(function () {
      undoStack.push(entry);
      showWidget(entry.label, 'Undo', undoLast);
    });
  }
  function pushHistory(entry) {
    undoStack.push(entry);
    if (undoStack.length > MAX_HISTORY) undoStack.shift();
    redoStack = [];
    showWidget(entry.label, 'Undo', undoLast);
  }

  /* ---------- db ---------- */
  function docRef(collName, id) {
    return {
      get: function () {
        return idbGet(collName, id).then(function (v) {
          return { exists: v !== undefined, data: function () { return v; } };
        });
      },
      set: function (value, opts) {
        var clone = JSON.parse(JSON.stringify(value));
        if (TRACKED[collName] && !(opts && opts.silent)) {
          return idbGet(collName, id).then(function (prev) {
            return idbSet(collName, id, clone).then(function () {
              pushHistory({ collection: collName, id: id, prevValue: prev, newValue: clone, label: labelFor(collName, id, prev, clone, 'set') });
              notify(collName);
            });
          });
        }
        return idbSet(collName, id, clone).then(function () { notify(collName); });
      },
      delete: function () {
        if (TRACKED[collName]) {
          return idbGet(collName, id).then(function (prev) {
            return idbDelete(collName, id).then(function () {
              pushHistory({ collection: collName, id: id, prevValue: prev, newValue: undefined, label: labelFor(collName, id, prev, undefined, 'delete') });
              notify(collName);
            });
          });
        }
        return idbDelete(collName, id).then(function () { notify(collName); });
      },
      onSnapshot: function (cb, errCb) {
        return addListener(collName, function () {
          idbGet(collName, id).then(function (v) {
            cb({ exists: v !== undefined, data: function () { return v; } });
          }).catch(function (e) { if (errCb) errCb(e); });
        });
      }
    };
  }
  function collectionRef(name, opts) {
    opts = opts || {};
    return {
      orderBy: function (field, dir) { return collectionRef(name, Object.assign({}, opts, { orderByField: field, orderDir: dir || 'asc' })); },
      limit: function (n) { return collectionRef(name, Object.assign({}, opts, { limitN: n })); },
      doc: function (id) { return docRef(name, id); },
      onSnapshot: function (cb, errCb) {
        return addListener(name, function () {
          idbScan(name).then(function (rows) {
            var docs = rows.map(function (r) { return { id: r.id, data: function () { return r.value; } }; });
            if (opts.orderByField) {
              docs.sort(function (a, b) {
                var av = a.data()[opts.orderByField], bv = b.data()[opts.orderByField];
                var cmp = av < bv ? -1 : av > bv ? 1 : 0;
                return opts.orderDir === 'desc' ? -cmp : cmp;
              });
            }
            if (opts.limitN) docs = docs.slice(0, opts.limitN);
            cb({ docs: docs });
          }).catch(function (e) { if (errCb) errCb(e); });
        });
      }
    };
  }
  var db = {
    collection: function (name) { return collectionRef(name); },
    doc: function (path) {
      var i = path.indexOf('/');
      var collName = i === -1 ? path : path.slice(0, i);
      var id = i === -1 ? '' : path.slice(i + 1);
      return docRef(collName, id);
    }
  };

  /* ---------- user ---------- */
  var LOCAL_ID = 'local-owner';
  var user = {
    id: function () { return Promise.resolve(LOCAL_ID); },
    name: function () { return Promise.resolve('You'); },
    can: function () { return Promise.resolve(true); },
    isOwner: function () { return Promise.resolve(true); },
    profiles: function (ids) {
      var out = {};
      (ids || []).forEach(function (id) { out[id] = { name: id === LOCAL_ID ? 'You' : 'Teammate' }; });
      return Promise.resolve(out);
    },
    search: function () { return Promise.resolve([]); } // no org directory on a local machine
  };

  /* ---------- downloads ---------- */
  var downloads = {
    save: function (opts) {
      var filename = opts.filename, data = opts.data;
      var blob = data instanceof Blob ? data : new Blob([data]);
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url; a.download = filename;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
      return Promise.resolve();
    }
  };

  window.claude = {
    use: function (name) {
      if (name === 'db') return Promise.resolve(db);
      if (name === 'user') return Promise.resolve(user);
      if (name === 'downloads') return Promise.resolve(downloads);
      return Promise.resolve(null);
    }
  };
})();
