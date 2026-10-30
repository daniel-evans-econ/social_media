(() => {
  'use strict';
  const $ = id => document.getElementById('selfie-' + id);
  const form = document.querySelector('form'), video = $('camera'), result = $('result');
  let stream = null, image = '', saved = false, request = 0, saving = false;
  function stop() {
    request++;
    if (stream) stream.getTracks().forEach(track => track.stop());
    stream = null; video.srcObject = null;
  }
  async function open() {
    stop(); const current = request; image = '';
    result.removeAttribute('src'); result.hidden = true;
    $('preview').hidden = true;
    $('confirm').hidden = true; $('retake').hidden = true; $('open').disabled = true;
    $('status').textContent = 'Please allow camera access.';
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error('Camera unavailable');
      const camera = await navigator.mediaDevices.getUserMedia({video:{facingMode:'user'},audio:false});
      if (current !== request) { camera.getTracks().forEach(track => track.stop()); return; }
      stream = camera; video.srcObject = camera; video.hidden = false;
      await video.play();
      $('take').hidden = false; $('open').hidden = true; $('status').textContent = '';
    } catch (_) {
      stop(); video.hidden = true;
      $('status').textContent = 'Camera access is unavailable. Please allow camera access in your browser and try again. You can contact the research team through Prolific if you cannot continue.';
    } finally { $('open').disabled = false; }
  }
  $('open').onclick = open; $('retake').onclick = open;
  $('take').onclick = () => {
    if (!video.videoWidth) return;
    const source = document.createElement('canvas'); source.width = source.height = 512;
    const context = source.getContext('2d'), side = Math.min(video.videoWidth,video.videoHeight);
    context.translate(512,0); context.scale(-1,1);
    context.drawImage(video,(video.videoWidth-side)/2,(video.videoHeight-side)/2,side,side,0,0,512,512);
    const padded = document.createElement('canvas'); padded.width = padded.height = 832;
    const pc = padded.getContext('2d'), p = 160, s = 512;
    pc.drawImage(source,p,p);
    pc.drawImage(source,0,0,s,1,p,0,s,p); pc.drawImage(source,0,s-1,s,1,p,p+s,s,p);
    pc.drawImage(source,0,0,1,s,0,p,p,s); pc.drawImage(source,s-1,0,1,s,p+s,p,p,s);
    for (const x of [0,1]) for (const y of [0,1])
      pc.drawImage(source,x*(s-1),y*(s-1),1,1,x*(p+s),y*(p+s),p,p);
    const blurred = document.createElement('canvas'); blurred.width = blurred.height = 512;
    const bc = blurred.getContext('2d');
    // Canvas filtering is required. Never fall back to uploading an unblurred image.
    bc.filter = 'blur(10px)';
    if (bc.filter !== 'blur(10px)') {
      stop(); source.width = padded.width = 0; video.hidden = true; $('take').hidden = true;
      $('open').hidden = false;
      $('status').textContent = 'This browser cannot blur selfies safely. Please use a current browser such as Chrome or Firefox.';
      return;
    }
    bc.drawImage(padded,-p,-p);
    // Keep blur strength on the original 512px scale; transmit only the
    // 72px thumbnail (2x resolution for its 36px message display).
    const thumbnail = document.createElement('canvas'); thumbnail.width = thumbnail.height = 72;
    thumbnail.getContext('2d').drawImage(blurred,0,0,72,72);
    image = thumbnail.toDataURL('image/jpeg',0.9);
    source.width = padded.width = blurred.width = thumbnail.width = 0; stop();
    video.hidden = true; $('take').hidden = true;
    result.src = image; result.hidden = false; $('retake').hidden = false; $('confirm').hidden = false;
    $('preview').hidden = false;
    $('status').textContent = 'Is this the selfie you would like to use?';
  };
  $('confirm').onclick = () => {
    if (!image || saving) return;
    saving = true; $('confirm').disabled = true; $('retake').disabled = true;
    $('status').textContent = 'Saving your blurred selfie…';
    liveSend({action:'confirm',image});
  };
  window.liveRecv = data => {
    if (data.saved) { saved = true; image = ''; form.requestSubmit(); }
    else { saving = false; $('confirm').disabled = false; $('retake').disabled = false; $('status').textContent = data.error || 'Please try again.'; }
  };
  form.addEventListener('submit',event => { if (!saved) event.preventDefault(); });
  window.addEventListener('pagehide',stop);
})();
