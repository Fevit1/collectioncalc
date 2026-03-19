export async function onRequest(context) {
  const url = new URL(context.request.url);
  
  // If domain is collectioncalc.com, serve collectioncalc.html
  if (url.hostname === 'collectioncalc.com' || url.hostname === 'www.collectioncalc.com') {
    return context.env.ASSETS.fetch(new URL('/collectioncalc.html', url.origin));
  }
  
  // Otherwise continue normally (serve SlabWorthy)
  return context.next();
}