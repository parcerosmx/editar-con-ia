// Caras y textos en cada imagen, con Vision de macOS (todo en la Mac, nada sale a internet).
// Uso: osascript -l JavaScript herramientas/vision.js cuadro1.png cuadro2.png ...
// Imprime JSON: {"cuadro1.png": {"caras": [[x0,y0,x1,y1], ...], "textos": [{"t": "...", "caja": [x0,y0,x1,y1]}]}}
// Las cajas van en fracciones del cuadro (0 a 1), con y=0 ARRIBA.
ObjC.import('Foundation'); ObjC.import('Vision')
function caja(b) { return [b.origin.x, 1 - b.origin.y - b.size.height, b.origin.x + b.size.width, 1 - b.origin.y] }
function run(argv) {
  const out = {}
  for (const f of argv) {
    const h = $.VNImageRequestHandler.alloc.initWithURLOptions($.NSURL.fileURLWithPath(f), $())
    const rc = $.VNDetectFaceRectanglesRequest.alloc.init
    const rt = $.VNRecognizeTextRequest.alloc.init
    rt.recognitionLevel = 0            // 0 = preciso
    rt.recognitionLanguages = $(['es-ES', 'en-US'])
    h.performRequestsError($([rc, rt]), $())
    const caras = [], textos = []
    const a = rc.results
    for (let i = 0; i < a.count; i++) caras.push(caja(a.objectAtIndex(i).boundingBox))
    const b = rt.results
    for (let i = 0; i < b.count; i++) {
      const o = b.objectAtIndex(i)
      textos.push({ t: o.topCandidates(1).objectAtIndex(0).string.js, caja: caja(o.boundingBox) })
    }
    out[f] = { caras: caras, textos: textos }
  }
  return JSON.stringify(out)
}
