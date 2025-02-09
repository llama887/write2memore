onloadAdd(() => {
    let keystrokeCount = 0;
    me("textarea").on("keydown", ev => {
        let textarea = me(ev); // Get the textarea element
        keystrokeCount++; // Increment the keystroke count
        if (keystrokeCount % 50 === 0 && keystrokeCount >= 50) {
            htmx.ajax("POST", "/prompt_user", {
                target: "#diary-prompt",
                swap: "innerHTML",
                values: { text: textarea.value }
            }).catch(err => console.warn("Request failed:", err));
        }
    });
});