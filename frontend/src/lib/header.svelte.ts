/** Lets a page put its own title in the shell's top bar. */
class HeaderStore {
  title = $state<string>("");
  subtitle = $state<string>("");

  set(title: string, subtitle = "") {
    this.title = title;
    this.subtitle = subtitle;
  }

  clear() {
    this.title = "";
    this.subtitle = "";
  }
}

export const header = new HeaderStore();
