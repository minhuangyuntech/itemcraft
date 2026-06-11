(function () {
  const certificationNotes = {
    "AI法規與資安風險管理": "對應之AI安全、法規規範等內容",
    "AI應用下的倫理準則與智慧財產權實務": "對應之智慧財產權、AI倫理原則等內容",
  };

  function showMessage(text) {
    const message = document.getElementById("split-original-message");
    if (!message) return;
    message.textContent = text;
    message.classList.remove("d-none");
  }

  function hideMessage() {
    const message = document.getElementById("split-original-message");
    if (!message) return;
    message.textContent = "";
    message.classList.add("d-none");
  }

  function splitOptions(text) {
    const markerPattern = /(?:^|[\r\n])\s*([ABCD])[\.\)、）:：]\s*/g;
    const matches = Array.from(text.matchAll(markerPattern));
    const labels = matches.map((match) => match[1]);
    const uniqueLabels = new Set(labels);

    if (matches.length < 4 || uniqueLabels.size < 4) {
      return null;
    }

    const first = matches[0];
    const result = {
      stem: text.slice(0, first.index).trim(),
      A: "",
      B: "",
      C: "",
      D: "",
    };

    matches.forEach((match, index) => {
      const label = match[1];
      const start = match.index + match[0].length;
      const end = index + 1 < matches.length ? matches[index + 1].index : text.length;
      result[label] = text.slice(start, end).trim();
    });

    return result;
  }

  function bindOptionSplitter() {
    const button = document.getElementById("split-original-options");
    const stem = document.getElementById("id_stem");
    const choiceA = document.getElementById("id_choice_a");
    const choiceB = document.getElementById("id_choice_b");
    const choiceC = document.getElementById("id_choice_c");
    const choiceD = document.getElementById("id_choice_d");

    if (!button || !stem || !choiceA || !choiceB || !choiceC || !choiceD) return;

    button.addEventListener("click", function () {
      hideMessage();
      const parsed = splitOptions(stem.value);
      if (!parsed) {
        showMessage("找不到完整的 A-D 選項，請確認內容中包含 A.、A:、A：或 A、等格式。");
        return;
      }

      stem.value = parsed.stem;
      choiceA.value = parsed.A;
      choiceB.value = parsed.B;
      choiceC.value = parsed.C;
      choiceD.value = parsed.D;
      showMessage("已拆解 A-D 選項，並已從題幹移除選項內容。");
    });
  }

  function bindCertificationNoteSync() {
    const subDimension = document.getElementById("id_sub_dimension");
    const certificationNote = document.getElementById("id_certification_note");

    if (!subDimension || !certificationNote) return;

    function syncNote() {
      const note = certificationNotes[subDimension.value] || "";
      certificationNote.value = note;
    }

    subDimension.addEventListener("change", syncNote);
    if (!certificationNote.value.trim()) {
      syncNote();
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindOptionSplitter();
    bindCertificationNoteSync();
  });
})();
