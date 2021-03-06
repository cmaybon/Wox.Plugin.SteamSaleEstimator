# SteamSaleEstimator
Used to estimate the net revenue of a Steam title.
> After install you should navigate to the plugin install directory and change `data.json` to reflect the localisation you want.  
> Default language is `en`, default currency is `aud` if `data.json` cannot be read.

## Example usage:
`steames https://store.steampowered.com/app/892970/Valheim/`

<br/>

![Preview](preview.gif)

## NOTE
These are only estimates based on the amount of reviews, release date, and estimated average revenue cut. These numbers may be completely inaccurate.  

The method for estimating sold copies is using the New Boxleiter ratios which you can read more at [here](https://newsletter.gamediscover.co/p/how-that-game-sold-on-steam-using) and [here](https://www.gamedeveloper.com/business/how-to-estimate-steam-video-game-sales-in-2021-).

The revenue cut estimations are 30-50% of the game's steam retail price. This is to account for Steam's cut, VAT, refunds and discounts.
The "best guess" number is the median of the above range.

---

### Requirements
Python packages:
* requests

