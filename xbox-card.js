import { LitElement, html, css } from "https://unpkg.com/lit-element@3.2.2/index.js?module";

class XboxCard extends LitElement {
  static get properties() {
    return {
      hass: {},
      config: {},
      images: { type: Array },
      activeImage: { type: Object },
      gameBackground: { type: String },
      backgroundImage: { type: String },
      imageIndex: { type: Number }
    };
  }

  constructor() {
    super();
    this.gameBackground = '';
    this.backgroundImage = '';
    this.imageIndex = 0;
  }

  // Component lifecycle methods
  updated(changedProperties) {
    if (changedProperties.has('backgroundImage')) {
      this.shadowRoot.querySelector('.image-container').style.setProperty('--background-image', this.backgroundImage);
    }
  }

  firstUpdated() {
    this.startImageRotation();
  }

  // Utility methods
  handleGalleryImageClick(imageUrl) {
    this.backgroundImage = `url(${imageUrl.url})`;
    this.imageIndex = (this.imageIndex + 1) % this.images.length;
  }

  startImageRotation() {
    setInterval(() => {
      const imageUrl = this.images[this.imageIndex];
      this.handleGalleryImageClick(imageUrl);
    }, 10000); // change the interval time as per your requirement
  }

  // Render method
  render() {
    return html`
      ${this.config.entities.map((ent) => {
        const stateObj = this.hass.states[ent];
        const entityId = this.config.entities;
        const state = this.hass.states[entityId];
        this.images = state.attributes.events.screenshot;

        return state
          ? html`
              <div class="card">
                <div class="image-container">
                  <img class="game-image" src="${state.attributes.events.title_box_art}" alt="Game image" />
                  <img
                    class="console-icon"
                    src="https://cdn.iconscout.com/icon/free/png-256/xbox-49-722654.png?f=webp&w=256"
                    alt="Xbox Series S Icon"
                  />
                  <div class="gamerpic">
                    <img src="${state.attributes.events.display_pic_raw}" alt="Gamerpic" />
                   
                  </div>
                  
                </div>
                <div class="game-info">
                  <h2 class="game-title">${state.attributes.events.title_name}</h2>
                  <div class="game-details">
                    <p class="game-publisher">${state.attributes.events.title_publisher_name}</p>
                    <p class="game-age">${state.attributes.events.min_age}+</p>
                  </div>
                  <p class="game-description">${state.attributes.events.title_description}</p>
                  <div class="hd">
                    <h1 class="console_name">${state.attributes.events.console_name}</h1>
                    <progress
                      max="${state.attributes.events.total_space}"
                      value="${state.attributes.events.total_space - state.attributes.events.free_space}"
                      ></progress>
                    <br/>
                    <span class="progress-label">${state.attributes.events.free_space}GB free of ${state.attributes.events.total_space}GB</span>
                    <br/>
                  </div>
                  <div class="game-gallery">
                    ${state.attributes.events.screenshot.map(
                      (imageUrl) =>
                        html`<img
                          src="${imageUrl.url}"
                          alt="Game gallery image"
                          @click="${() => this.handleGalleryImageClick(imageUrl)}"
                        />`
                    )}
                    </div>
                    </div>
                  </div>
                `
              : html;
          })}
        `;
        
        }

  setConfig(config) {
    if (!config.entities) {
      throw new Error("You need to define entities");
    }

    this.config = config;
  }

  getCardSize() {
    return this.config.entities.length + 1;
  }

  static get styles() {
    return css`
    .card {
      display: flex;
      flex-direction: column;
      background-color: #111;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
      overflow: hidden;
      margin-bottom: 16px;
    }
    
    .image-container {
      position: relative;
      height: 400px;
      width: 100%;
      background-size: cover;
      background-position: center center;
      background-repeat: no-repeat;
      background-image: var(--background-image);
      transition: opacity 0.5s ease;
    }
    
    .game-image {
      position: absolute;
      bottom: 16px;
      left: 16px;
      height: 25%;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    
    .console-icon {
      position: absolute;
      top: 10px;
      left: 16px;
      width: 24px;
      height: 24px;
    }
    
    .gamerpic {
      position: absolute;
      bottom: 16px;
      right: 16px;
      width: 32px;
      height: 32px;
      border: 2px solid white;
      border-radius: 50%;
      overflow: hidden;
    }
    
    .gamerpic img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    
    .gamerpic span {
      display: block;
      text-align: center;
      color: #fff;
      margin-top: 4px;
    }
    
    .console_name {
      font-size: 16px;
      font-weight: bold;
    }
    
    .game-info {
      padding: 16px;
      color: white;
    }
    
    .game-title {
      font-size: 24px;
      font-weight: bold;
      margin-top: 0;
      margin-bottom: 8px;
      color: white;
    }
    
    .game-description {
      font-size: 16px;
      margin-bottom: 16px;
      color: white;
    }
    
    .game-gallery {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      grid-gap: 16px;
      padding-top: 10px;
    }
    
    .game-gallery img {
      height: 100%;
      width: 100%;
      object-fit: cover;
      cursor: pointer;
      border-radius: 8px;
      transition: transform 0.2s ease-in-out;
    }
    
    .game-gallery img:hover {
      transform: scale(1.1);
    }
    
    .progress {
      width: 100%;
      height: 5px;
      margin-top: 8px;
      border-radius: 5px;
      background-color: #e0e0e0;
      position: relative;
    }
    
    .progress-bar {
      height: 100%;
      border-radius: 5px;
      background-color: #1d9bf0;
      transition: width 0.2s ease-in-out;
    }
    
    .progress-label {
      font-size: 14px;
      text-align: center;
      color: #777;
      margin-top: 8px;
    }
    
    .game-details {
      display: flex;
      align-items: center;
      margin-bottom: 8px;
    }
    
    .game-publisher {
      font-size: 16px;
      font-weight: bold;
      margin-right: 16px;
    }
    
    .game-age {
      font-size: 16px;
      font-weight: bold;
      background-color: #1d9bf0;
      color: white;
      padding: 2px 8px;
      border-radius: 16px;
      text-transform: uppercase;
      letter-spacing: 1px;
      }
      
      /* Improve responsiveness for smaller screens */
      @media only screen and (max-width: 768px) {
      .image-container {
      height: 200px;
      }
      
      .game-image {
      height: 50%;
      }
      
      .game-title {
      font-size: 20px;
      }
      
      .game-description {
      font-size: 14px;
      }
      
      .game-gallery {
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      grid-gap: 8px;
      }
      
      .game-gallery img {
      border-radius: 4px;
      }
      
      .game-publisher,
      .game-age {
      font-size: 14px;
      }
      }
    
    
    
    
    `;
  }
}

customElements.define("xbox-card", XboxCard);    
