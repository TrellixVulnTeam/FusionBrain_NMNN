import torch


def cross_vqa_evaluation(model, images, tokens, attention_masks, max_answer_length):
    back_out = model.backbone(images)
    patchs = model.input_proj(back_out).flatten(-2).transpose(-1, -2)
    gpt_img = model.gpt_model(inputs_embeds=patchs).last_hidden_state

    answer_logits = []
    bs = gpt_img.shape[0]
    for _ in range(max_answer_length):
        gpt_text = model.gpt_model(input_ids=tokens, attention_mask=attention_masks).last_hidden_state
        for layer in model.cross_attention:
            gpt_text, _ = layer(gpt_text, gpt_img)

        logits = model.tokens_embed(gpt_text)
        last_logits = logits[:, -1, :]
        answer_logits.append(last_logits)

        new_tokens = torch.multinomial(last_logits.softmax(-1), num_samples=1)
        tokens = torch.cat([tokens, new_tokens], dim=-1)
        new_attention_masks = torch.ones(bs, 1).to(attention_masks.device, dtype=attention_masks.dtype)
        attention_masks = torch.cat([attention_masks, new_attention_masks], dim=1)

    return torch.stack(answer_logits, dim=1)


def inverse_vqa_evaluation(model, images, tokens, max_answer_length):
    back_out = model.backbone(images)
    img_embeddings = model.input_proj(back_out).flatten(-2).transpose(-1, -2)

    answer_logits = []
    for _ in range(max_answer_length):
        tokens_embeddings = model.gpt_model.wte(tokens) + model.gpt_model.wpe(
            torch.arange(tokens.shape[1], device=tokens.device))
        embedings = torch.cat((img_embeddings, tokens_embeddings), dim=1)
        gpt_out = model.gpt_model(inputs_embeds=embedings).last_hidden_state

        logits = model.tokens_embed(gpt_out)
        last_logits = logits[:, -1, :]
        answer_logits.append(last_logits)

        new_tokens = torch.multinomial(last_logits.softmax(-1), num_samples=1)
        tokens = torch.cat([tokens, new_tokens], dim=-1)
        if new_tokens[0].item() == 2:
            break

    return torch.stack(answer_logits, dim=1)
