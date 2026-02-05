"""Local LLM Adapter for GPU-based inference using HuggingFace Transformers.

This adapter provides a drop-in replacement for the API-based LLMAdapter,
enabling local GPU inference with models like Qwen2.5-Coder or DeepSeek-Coder.

Usage:
    # Set environment variables
    export LLM_TYPE=transformers
    export LLM_MODEL_ID=Qwen/Qwen2.5-Coder-32B-Instruct
    export LLM_QUANTIZATION=none  # or "4bit" or "8bit"

    # Use via factory
    from src.core.llm_adapter import create_llm_adapter
    llm = create_llm_adapter()
"""

import re
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.contracts import ToolContract

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

from src.config import (
    LLM_MODEL_ID, LLM_QUANTIZATION, LLM_DEVICE,
    LLM_TEMPERATURE, LLM_MAX_NEW_TOKENS
)
from src.core.llm_adapter import PROMPT_BY_CATEGORY, SYSTEM_PROMPT


class LocalLLMAdapter:
    """HuggingFace Transformers adapter for local GPU inference."""

    _instance = None
    _model = None
    _tokenizer = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to avoid reloading model."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        model_id: str = LLM_MODEL_ID,
        quantization: str = LLM_QUANTIZATION,
        device: str = LLM_DEVICE,
        temperature: float = LLM_TEMPERATURE,
        max_new_tokens: int = LLM_MAX_NEW_TOKENS
    ):
        # Skip re-initialization if already loaded
        if self._model is not None:
            return

        self.model_id = model_id
        self.quantization = quantization
        self.device = device
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens

        self._load_model()

    def _load_model(self):
        """Load model and tokenizer with optional quantization."""
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        except ImportError as e:
            raise ImportError(
                "GPU dependencies not installed. Run: pip install -r requirements-gpu.txt"
            ) from e

        print(f"[LocalLLM] Loading model: {self.model_id}")
        print(f"[LocalLLM] Quantization: {self.quantization}, Device: {self.device}")

        # Configure quantization
        quantization_config = None
        torch_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16

        if self.quantization == "4bit":
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch_dtype,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )
        elif self.quantization == "8bit":
            quantization_config = BitsAndBytesConfig(
                load_in_8bit=True,
            )

        # Load tokenizer
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_id,
            trust_remote_code=True
        )

        # Load model
        model_kwargs = {
            "trust_remote_code": True,
            "device_map": "auto" if self.device == "cuda" else self.device,
        }

        if quantization_config:
            model_kwargs["quantization_config"] = quantization_config
        else:
            model_kwargs["torch_dtype"] = torch_dtype

        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            **model_kwargs
        )

        # Get GPU memory usage
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024**3
            reserved = torch.cuda.memory_reserved() / 1024**3
            print(f"[LocalLLM] GPU Memory: {allocated:.1f}GB allocated, {reserved:.1f}GB reserved")

        print(f"[LocalLLM] Model loaded successfully!")

    def _clean_protocol(self, raw_content: str) -> dict:
        """Clean LLM response protocol (same as API adapter)."""
        # Extract thinking trace
        think_match = re.search(r"<think>(.*?)</think>", raw_content, re.DOTALL)
        thought_trace = think_match.group(1).strip() if think_match else ""

        # Remove thinking tags for clean text
        text_response = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL).strip()

        # Extract Python code block
        code_match = re.search(r"```python(.*?)```", text_response, re.DOTALL)
        code_payload = code_match.group(1).strip() if code_match else None

        return {
            "thought_trace": thought_trace,
            "code_payload": code_payload,
            "text_response": text_response
        }

    def generate_tool_code(
        self,
        task: str,
        error_context: Optional[str] = None,
        category: Optional[str] = None,
        contract: Optional['ToolContract'] = None
    ) -> dict:
        """Generate tool code using local model."""
        import torch

        # Select system prompt based on category
        if category and category in PROMPT_BY_CATEGORY:
            system_prompt = PROMPT_BY_CATEGORY[category]
        else:
            # Infer category from task
            task_lower = task.lower()
            if any(kw in task_lower for kw in ['fetch', 'get', '获取', '查询', 'price', 'quote']):
                if any(kw in task_lower for kw in ['calculate', 'calc', '计算', 'rsi', 'macd', 'bollinger']):
                    category = 'calculation'
                else:
                    category = 'fetch'
            elif any(kw in task_lower for kw in ['if ', 'return true', 'return false', 'signal', 'divergence', 'portfolio']):
                category = 'composite'
            else:
                category = 'calculation'
            system_prompt = PROMPT_BY_CATEGORY.get(category, SYSTEM_PROMPT)

        # Build user prompt
        user_prompt = f"Task: {task}"

        # Add contract constraint
        if contract:
            constraint = self._format_output_constraint(contract)
            if constraint:
                user_prompt += f"\n\nOUTPUT: {constraint}"

        if error_context:
            user_prompt += f"\n\nPrevious Error:\n{error_context}\n\nFix the issue."

        # Format messages for chat model
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            # Apply chat template
            text = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )

            # Tokenize
            model_inputs = self._tokenizer([text], return_tensors="pt").to(self._model.device)

            # Generate
            with torch.no_grad():
                generated_ids = self._model.generate(
                    **model_inputs,
                    max_new_tokens=self.max_new_tokens,
                    temperature=self.temperature if self.temperature > 0 else None,
                    do_sample=self.temperature > 0,
                    pad_token_id=self._tokenizer.eos_token_id,
                )

            # Decode only new tokens
            generated_ids = generated_ids[:, model_inputs.input_ids.shape[1]:]
            raw_response = self._tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

            parsed = self._clean_protocol(raw_response)
            return {
                "thought_trace": parsed["thought_trace"],
                "code_payload": parsed["code_payload"],
                "text_response": parsed["text_response"],
                "raw_response": raw_response,
                "category": category
            }

        except Exception as e:
            print(f"[LocalLLM Error] {e}")
            return {
                "thought_trace": "",
                "code_payload": None,
                "text_response": f"Local LLM Error: {e}",
                "raw_response": f"Local LLM Error: {e}",
                "category": category
            }

    def _format_output_constraint(self, contract: 'ToolContract') -> str:
        """Format contract as output constraint (same as API adapter)."""
        output_type = contract.output_type.value if hasattr(contract.output_type, 'value') else str(contract.output_type)

        if output_type == "numeric":
            return "Return a single float. Do NOT return dict/DataFrame/list."
        elif output_type == "dict":
            keys = getattr(contract, 'required_keys', None) or []
            if keys:
                return f"Return a dict with keys: {keys}. Do NOT return DataFrame/list."
            return "Return a dict. Do NOT return DataFrame/list."
        elif output_type == "boolean":
            return "Return True or False. Do NOT return 0/1 or string."
        elif output_type == "dataframe":
            keys = getattr(contract, 'required_keys', None) or []
            if keys:
                return f"Return a DataFrame with columns: {keys}."
            return "Return a DataFrame."
        elif output_type == "list":
            return "Return a list. Do NOT return dict/DataFrame."
        return ""


if __name__ == "__main__":
    # Test local adapter
    print("Testing LocalLLMAdapter...")

    # This will fail if GPU deps not installed - that's expected
    try:
        adapter = LocalLLMAdapter(
            model_id="Qwen/Qwen2.5-Coder-7B-Instruct",  # Smaller for testing
            quantization="4bit"
        )

        result = adapter.generate_tool_code("计算 RSI 指标", category="calculation")
        print(f"Generated code: {len(result.get('code_payload') or '')} chars")
        print(f"Category: {result.get('category')}")
    except ImportError as e:
        print(f"GPU dependencies not available: {e}")
        print("Install with: pip install -r requirements-gpu.txt")
