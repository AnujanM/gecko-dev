/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

// Test that the debugger pauses in the omniscient browser toolbox even when it
// hasn't been opened.

"use strict";

requestLongerTimeout(4);

Services.scriptloader.loadSubScript(
  "chrome://mochitests/content/browser/devtools/client/framework/test/helpers.js",
  this
);

add_task(async function() {
  await pushPref("devtools.browsertoolbox.fission", true);

  // Make sure the toolbox opens with the webconsole initially selected.
  await pushPref("devtools.browsertoolbox.panel", "webconsole");

  const ToolboxTask = await initBrowserToolboxTask();
  await ToolboxTask.importFunctions({
    waitUntil,
    waitForPaused,
    isPaused,
    waitForState,
    info: () => {},
    waitForSelectedSource,
    waitForLoadedScopes: () => {},
  });

  addTab("data:text/html,<script>debugger;</script>");

  // The debugger should automatically be selected.
  await ToolboxTask.spawn(null, async () => {
    await waitUntil(() => gToolbox.currentToolId == "jsdebugger");
  });
  ok(true, "Debugger selected");

  // The debugger should pause.
  await ToolboxTask.spawn(null, async () => {
    // Wait for the debugger to finish loading.
    await gToolbox.selectTool("jsdebugger");

    const dbg = gToolbox.getCurrentPanel().panelWin.dbg;
    await waitForPaused(dbg);
    if (!gToolbox.isToolHighlighted("jsdebugger")) {
      throw new Error("Debugger not highlighted");
    }
  });
  ok(true, "Paused in new tab");

  await ToolboxTask.destroy();
});
