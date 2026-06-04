import { continueRender, delayRender, staticFile } from "remotion";

const fontFamily = "Pretendard";
const handle = delayRender("Load Pretendard font");

if (typeof document !== "undefined") {
  const fontUrl = staticFile("fonts/PretendardVariable.woff2");

  const preload = document.createElement("link");
  preload.rel = "preload";
  preload.href = fontUrl;
  preload.as = "font";
  preload.type = "font/woff2";
  preload.crossOrigin = "anonymous";
  document.head.appendChild(preload);

  const style = document.createElement("style");
  style.appendChild(
    document.createTextNode(`
@font-face {
  font-family: '${fontFamily}';
  src: url('${fontUrl}') format('woff2');
  font-weight: 100 900;
  font-display: block;
  font-style: normal;
}
`)
  );
  document.head.appendChild(style);

  document.fonts
    .load(`16px ${fontFamily}`)
    .then(() => continueRender(handle))
    .catch((err) => {
      console.warn("Pretendard font load failed. Falling back to system fonts.", err);
      continueRender(handle);
    });
} else {
  continueRender(handle);
}