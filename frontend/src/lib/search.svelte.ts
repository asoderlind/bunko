/** Lets the sidebar open the shell's search field. */
class SearchStore {
  visible = $state(false);

  show() {
    this.visible = true;
  }

  hide() {
    this.visible = false;
  }
}

export const search = new SearchStore();
